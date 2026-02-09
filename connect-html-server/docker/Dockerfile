FROM alpine:latest

# Install Redpanda Connect
RUN apk add --no-cache curl tar && \
    LATEST_VERSION=$(curl -s https://api.github.com/repos/redpanda-data/connect/releases/latest | grep '"tag_name"' | cut -d'"' -f4) && \
    curl -Lsf "https://github.com/redpanda-data/connect/releases/download/${LATEST_VERSION}/redpanda-connect_${LATEST_VERSION#v}_linux_amd64.tar.gz" | \
    tar xzvf - -C /usr/local/bin && \
    chmod +x /usr/local/bin/redpanda-connect && \
    apk del curl tar
