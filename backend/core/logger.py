import logging
import sys

# Configure logging format
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

# Filter out frequent /health check requests from Uvicorn access logs to prevent flooding
class HealthCheckFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        if record.args and len(record.args) >= 3:
            # Uvicorn access logs store the HTTP path in record.args[2] (e.g. "/health")
            path = record.args[2]
            if isinstance(path, str) and path.startswith("/health"):
                return False
        return True

def setup_logger(name: str = "devdocs-agent") -> logging.Logger:
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)

    # Console handler
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter(LOG_FORMAT))
    
    if not logger.handlers:
        logger.addHandler(handler)
    
    # Configure and silence noisy third-party libraries
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("openai").setLevel(logging.WARNING)
    logging.getLogger("pymongo").setLevel(logging.WARNING)
    logging.getLogger("agentops").setLevel(logging.WARNING)
    logging.getLogger("agno").setLevel(logging.WARNING)
    
    # Add health check filter to Uvicorn access logger
    logging.getLogger("uvicorn.access").addFilter(HealthCheckFilter())
    
    return logger

logger = setup_logger()
