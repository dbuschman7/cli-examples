FROM timeflies/connect-alpine-base:latest      

# Install Python for subprocess execution
RUN apk add --no-cache python3

# Create necessary directories
RUN mkdir -p /config /streams /python

# Copy configuration files
COPY config.yaml /config/config.yaml
COPY python/ /python/
COPY streams/ /streams/

# Expose HTTP port
EXPOSE 4195

# Set working directory
WORKDIR /config

# Run Redpanda Connect in streams mode
CMD ["redpanda-connect", "streams", "/config/config.yaml"]
