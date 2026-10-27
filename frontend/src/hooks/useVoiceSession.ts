"use client"

import { useCallback, useEffect, useRef, useState } from "react"
import {
  Room,
  RoomEvent,
  Track,
  type Participant,
  type RemoteTrack,
  type RemoteTrackPublication,
} from "livekit-client"
import { fetchVoiceToken } from "@/lib/api"

export type VoiceStatus =
  | "idle"
  | "connecting"
  | "listening"
  | "thinking"
  | "speaking"
  | "error"

export interface VoiceTranscript {
  /** Stable id for the segment, so interim text can replace the final text. */
  id: string
  role: "user" | "assistant"
  text: string
  final: boolean
}

interface UseVoiceSessionOptions {
  token: string | null
  onTranscript: (transcript: VoiceTranscript) => void | Promise<void>
}

const TRANSCRIPTION_TOPIC = "lk.transcription"

export function useVoiceSession({ token, onTranscript }: UseVoiceSessionOptions) {
  const [active, setActive] = useState(false)
  const [status, setStatus] = useState<VoiceStatus>("idle")
  const [error, setError] = useState<string | null>(null)
  const [audioBlocked, setAudioBlocked] = useState(false)

  const roomRef = useRef<Room | null>(null)
  const startingRef = useRef(false)
  const stoppingRef = useRef(false)
  const agentTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const epochRef = useRef(0)
  const audioElementsRef = useRef<HTMLMediaElement[]>([])
  const segmentTextRef = useRef<Map<string, string>>(new Map())
  const finalizedSegmentsRef = useRef<Set<string>>(new Set())
  const onTranscriptRef = useRef(onTranscript)

  useEffect(() => {
    onTranscriptRef.current = onTranscript
  }, [onTranscript])

  const applyAgentState = useCallback((state: string | undefined) => {
    switch (state) {
      case "initializing":
        setStatus("connecting")
        break
      case "thinking":
        setStatus("thinking")
        break
      case "speaking":
        setStatus("speaking")
        break
      case "listening":
      case "idle":
        setStatus("listening")
        break
      default:
        break
    }
  }, [])

  const clearAgentTimeout = useCallback(() => {
    if (agentTimeoutRef.current !== null) {
      clearTimeout(agentTimeoutRef.current)
      agentTimeoutRef.current = null
    }
  }, [])

  const cleanupRoom = useCallback(
    async (room: Room | null) => {
      clearAgentTimeout()
      if (!room) return

      try {
        await room.localParticipant.setMicrophoneEnabled(false)
      } catch {
        // Microphone may already be gone.
      }

      room.removeAllListeners()
      room.unregisterTextStreamHandler(TRANSCRIPTION_TOPIC)

      try {
        await room.disconnect()
      } catch {
        // Already disconnected.
      }

      for (const element of audioElementsRef.current) {
        element.remove()
      }
      audioElementsRef.current = []
    },
    [clearAgentTimeout],
  )

  const stop = useCallback(async () => {
    if (stoppingRef.current) return
    stoppingRef.current = true
    epochRef.current += 1
    const room = roomRef.current
    roomRef.current = null
    startingRef.current = false

    clearAgentTimeout()
    segmentTextRef.current.clear()
    finalizedSegmentsRef.current.clear()

    // Update the UI before the async teardown so a fast restart cannot be
    // overwritten by the old session's final state changes.
    setActive(false)
    setStatus("idle")
    setAudioBlocked(false)

    try {
      await cleanupRoom(room)
    } finally {
      stoppingRef.current = false
    }
  }, [cleanupRoom, clearAgentTimeout])

  const start = useCallback(async () => {
    if (roomRef.current || startingRef.current || stoppingRef.current) return

    const epoch = epochRef.current + 1
    epochRef.current = epoch
    startingRef.current = true
    segmentTextRef.current.clear()
    finalizedSegmentsRef.current.clear()
    setError(null)
    setStatus("connecting")

    let room: Room | null = null

    try {
      const credentials = await fetchVoiceToken(token)
      if (epoch !== epochRef.current) return

      room = new Room({ adaptiveStream: true, dynacast: true })
      roomRef.current = room

      room.registerTextStreamHandler(
        TRANSCRIPTION_TOPIC,
        async (reader, participantInfo) => {
          if (epoch !== epochRef.current) return

          const attributes = reader.info.attributes ?? {}
          const segmentId = attributes["lk.segment_id"] || reader.info.id

          if (finalizedSegmentsRef.current.has(segmentId)) return

          // The agent publishes the user's transcript on the user's behalf, so
          // prefer that attribute over the stream sender identity.
          const sender =
            attributes["lk.publish_on_behalf"] || participantInfo.identity
          const role =
            sender === room?.localParticipant.identity ? "user" : "assistant"
          const messageId = `${role}:${segmentId}`

          let text = ""
          try {
            for await (const chunk of reader) {
              if (epoch !== epochRef.current) break
              text += chunk
              const previous = segmentTextRef.current.get(messageId) ?? ""
              if (text.length > previous.length) {
                segmentTextRef.current.set(messageId, text)
                void onTranscriptRef.current({
                  id: messageId,
                  role,
                  text,
                  final: false,
                })
              }
            }
          } catch {
            // A read can abort mid-stream; keep the partial text already shown.
          }

          if (epoch !== epochRef.current) return

          // The closing trailer carries lk.transcription_final=true, and the
          // client merges it into reader.info.attributes when the stream ends.
          const isFinal =
            reader.info.attributes?.["lk.transcription_final"] === "true"

          if (isFinal && text.trim()) {
            finalizedSegmentsRef.current.add(segmentId)
            segmentTextRef.current.set(messageId, text)
            await onTranscriptRef.current({
              id: messageId,
              role,
              text,
              final: true,
            })
          }
        },
      )

      room.on(
        RoomEvent.TrackSubscribed,
        (
          track: RemoteTrack,
          _publication: RemoteTrackPublication,
          _participant: Participant,
        ) => {
          if (track.kind !== Track.Kind.Audio) return

          const element = track.attach()
          element.autoplay = true
          element.style.display = "none"
          document.body.appendChild(element)
          audioElementsRef.current.push(element)

          element.play().catch(() => {
            // Playback can be blocked until the next user gesture.
          })
        },
      )

      room.on(RoomEvent.TrackUnsubscribed, (track: RemoteTrack) => {
        for (const element of track.detach()) {
          element.remove()
          audioElementsRef.current = audioElementsRef.current.filter(
            (item) => item !== element,
          )
        }
      })

      room.on(RoomEvent.ParticipantAttributesChanged, (changed, participant) => {
        if (!participant.isAgent || stoppingRef.current) return
        applyAgentState(changed["lk.agent.state"])
      })

      room.on(RoomEvent.ParticipantConnected, (participant) => {
        if (!participant.isAgent || stoppingRef.current) return
        clearAgentTimeout()
        applyAgentState(participant.attributes["lk.agent.state"])
      })

      room.on(RoomEvent.ParticipantDisconnected, (participant) => {
        if (!participant.isAgent || stoppingRef.current) return
        clearAgentTimeout()
        setError("The voice assistant disconnected. Start voice mode again.")
        setStatus("error")
        setActive(false)
        void stop()
      })

      room.on(RoomEvent.AudioPlaybackStatusChanged, () => {
        setAudioBlocked(!room?.canPlaybackAudio)
      })

      room.on(RoomEvent.Disconnected, () => {
        if (stoppingRef.current || roomRef.current !== room) return
        epochRef.current += 1
        clearAgentTimeout()
        roomRef.current = null
        startingRef.current = false
        for (const element of audioElementsRef.current) {
          element.remove()
        }
        audioElementsRef.current = []
        segmentTextRef.current.clear()
        finalizedSegmentsRef.current.clear()
        setError("Voice connection lost. Try again.")
        setActive(false)
        setStatus("idle")
        setAudioBlocked(false)
      })

      await room.connect(credentials.server_url, credentials.participant_token)
      if (epoch !== epochRef.current) {
        await cleanupRoom(room)
        return
      }

      await room.localParticipant.setMicrophoneEnabled(true)
      if (epoch !== epochRef.current) {
        await cleanupRoom(room)
        return
      }

      await room.startAudio().catch(() => {})
      if (epoch !== epochRef.current) {
        await cleanupRoom(room)
        return
      }
      setAudioBlocked(!room.canPlaybackAudio)
      setActive(true)
      setStatus("listening")

      const connectedRoom = room
      const existingAgent = Array.from(
        connectedRoom.remoteParticipants.values(),
      ).find((participant) => participant.isAgent)

      if (existingAgent) {
        applyAgentState(existingAgent.attributes["lk.agent.state"])
      } else {
        // The dispatch can fail silently when the worker is not running.
        agentTimeoutRef.current = setTimeout(() => {
          if (epoch !== epochRef.current) return
          if (
            Array.from(connectedRoom.remoteParticipants.values()).some(
              (participant) => participant.isAgent,
            )
          ) {
            return
          }

          setError(
            "The voice assistant did not join. Make sure the voice worker is running.",
          )
          setStatus("error")
          setActive(false)
          void stop()
        }, 20_000)
      }
    } catch (err) {
      await cleanupRoom(room)
      roomRef.current = null

      if (epoch !== epochRef.current) return

      const message =
        err instanceof DOMException && err.name === "NotAllowedError"
          ? "Microphone access was denied. Allow it in your browser and try again."
          : err instanceof Error
            ? err.message
            : "Could not start voice mode."

      setError(message)
      setStatus("error")
      setActive(false)
      setAudioBlocked(false)
    } finally {
      if (epoch === epochRef.current) {
        startingRef.current = false
      }
    }
  }, [token, applyAgentState, cleanupRoom, clearAgentTimeout, stop])

  const toggle = useCallback(() => {
    if (roomRef.current || startingRef.current || stoppingRef.current) {
      void stop()
    } else {
      void start()
    }
  }, [start, stop])

  const clearError = useCallback(() => {
    setError(null)
    setStatus("idle")
  }, [])

  const resumeAudio = useCallback(async () => {
    const room = roomRef.current
    if (!room) return
    await room.startAudio().catch(() => {})
    setAudioBlocked(!room.canPlaybackAudio)
  }, [])

  // Always release the microphone and the room when the page unmounts.
  useEffect(() => {
    return () => {
      epochRef.current += 1
      clearAgentTimeout()
      const room = roomRef.current
      roomRef.current = null
      void cleanupRoom(room)
    }
  }, [cleanupRoom, clearAgentTimeout])

  return {
    active,
    status,
    error,
    audioBlocked,
    start,
    stop,
    toggle,
    clearError,
    resumeAudio,
  }
}
