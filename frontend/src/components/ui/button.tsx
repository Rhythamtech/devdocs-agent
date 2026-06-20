import { Button as ButtonPrimitive } from "@base-ui/react/button"
import { cva, type VariantProps } from "class-variance-authority"

import { cn } from "@/lib/utils"

const buttonVariants = cva(
  "group/button inline-flex shrink-0 items-center justify-center gap-2 rounded-lg border border-transparent bg-clip-padding font-medium text-sm leading-none whitespace-nowrap transition-all duration-150 outline-none select-none focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/20 active:not-aria-[haspopup]:scale-[0.98] disabled:pointer-events-none disabled:opacity-50 aria-invalid:border-destructive aria-invalid:ring-3 aria-invalid:ring-destructive/20 [&_svg]:pointer-events-none [&_svg]:shrink-0 [&_svg:not([class*='size-'])]:size-4",
  {
    variants: {
      variant: {
        default: "bg-white text-[#374151] hover:bg-gray-50 border border-[#E5E7EB] shadow-sm",
        outline: "border border-[#E5E7EB] bg-transparent text-[#6B7280] hover:border-[#D1D5DB] hover:text-[#1A1A2E] hover:bg-white",
        secondary: "bg-[#F3F4F6] text-[#374151] hover:bg-[#E5E7EB]",
        ghost: "bg-transparent text-[#6B7280] hover:bg-[#F3F4F6] hover:text-[#1A1A2E]",
        destructive: "bg-red-50 text-[#DC2626] hover:bg-red-100 border border-red-200",
        link: "text-[#2D5AE0] underline-offset-4 hover:underline rounded-lg",
        primary: "bg-[#2D5AE0] text-white hover:bg-[#2450C8] font-semibold shadow-sm shadow-[#2D5AE0]/20",
      },
      size: {
        default: "h-10 px-4 py-2",
        xs: "h-7 px-2.5 text-xs",
        sm: "h-8 px-3 text-xs",
        lg: "h-12 px-6 text-base",
        icon: "size-10",
        "icon-xs": "size-7",
        "icon-sm": "size-8",
        "icon-lg": "size-12",
      },
    },
    defaultVariants: {
      variant: "default",
      size: "default",
    },
  }
)

function Button({
  className,
  variant = "default",
  size = "default",
  ...props
}: ButtonPrimitive.Props & VariantProps<typeof buttonVariants>) {
  return (
    <ButtonPrimitive
      data-slot="button"
      className={cn(buttonVariants({ variant, size, className }))}
      {...props}
    />
  )
}

export { Button, buttonVariants }
