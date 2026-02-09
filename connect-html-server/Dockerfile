FROM timeflies/connect-alpine-base:latest      

# Create necessary directories
RUN mkdir -p /config /streams

# Copy configuration files
COPY config.yaml /config/config.yaml

# Expose HTTP port
EXPOSE 4195

# Set working directory
WORKDIR /config

# Run Redpanda Connect in streams mode
CMD ["redpanda-connect", "streams", "/config/config.yaml"]
