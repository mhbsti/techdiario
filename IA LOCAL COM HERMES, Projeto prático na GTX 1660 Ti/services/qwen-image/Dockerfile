# =============================================================================
# Qwen-Image-2.1-GGUF Service - Build Instantaneo (Binario Oficial Pre-Compilado)
# =============================================================================
FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 \
    python3-pip \
    python3-pil \
    python3-numpy \
    python3-requests \
    libgomp1 \
    libvulkan1 \
    fonts-liberation \
    fonts-dejavu-core \
    curl \
    unzip \
    ca-certificates \
    && pip3 install --break-system-packages --no-cache-dir \
        fastapi==0.115.0 \
        uvicorn==0.30.6 \
        pydantic==2.9.2 \
    && rm -rf /var/lib/apt/lists/*

# Baixa o binario oficial pre-compilado do stable-diffusion.cpp (suporte nativo a Qwen-Image-2.1 GGUF)
WORKDIR /opt/sdcpp
RUN curl -L -o sd.zip "https://github.com/leejet/stable-diffusion.cpp/releases/download/master-975-95b3090/sd-master-95b3090-bin-Linux-Ubuntu-24.04-x86_64.zip" \
    && unzip -q sd.zip \
    && rm -f sd.zip \
    && find /opt/sdcpp -name "sd-cli" -exec cp {} /usr/local/bin/sd-cli \; \
    && find /opt/sdcpp -name "sd-server" -exec cp {} /usr/local/bin/sd-server \; \
    && find /opt/sdcpp -name "*.so*" -exec cp -P {} /usr/local/bin/ \; \
    && find /opt/sdcpp -name "*.so*" -exec cp -P {} /usr/lib/x86_64-linux-gnu/ \; \
    && ldconfig \
    && chmod +x /usr/local/bin/sd-cli /usr/local/bin/sd-server

WORKDIR /app
COPY overlay_utils.py /app/overlay_utils.py
COPY app.py /app/app.py

EXPOSE 8090
CMD ["python3", "-m", "uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8090"]
