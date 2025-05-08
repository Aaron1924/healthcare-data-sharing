FROM python:3.10-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    cmake \
    git \
    curl \
    nodejs \
    npm \
    libgmp-dev \
    libgmp10 \
    libgmpxx4ldbl \
    && rm -rf /var/lib/apt/lists/*

# Clone and build MCL library
RUN git clone https://github.com/herumi/mcl.git && \
    cd mcl && \
    mkdir -p build && \
    cd build && \
    cmake .. && \
    make && \
    cd ../..

# Set MCL_LIB_PATH environment variable
ENV MCL_LIB_PATH=/usr/local/lib/mcl

# Create directory and symlink for MCL library
RUN mkdir -p /usr/local/lib/mcl && \
    cp -r /app/mcl/build/lib/* /usr/local/lib/mcl/ && \
    ldconfig

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application
COPY . .

# Install Node.js dependencies with retry logic
RUN cd /app && \
    for i in 1 2 3 4 5; do \
        echo "Attempt $i: Installing npm dependencies..." && \
        npm install && break || \
        echo "Attempt $i failed! Retrying in 10 seconds..." && \
        sleep 10; \
    done

# Compile the smart contract with retry logic
RUN cd /app && \
    for i in 1 2 3; do \
        echo "Attempt $i: Compiling smart contracts..." && \
        npm run compile && break || \
        echo "Attempt $i failed! Retrying in 5 seconds..." && \
        sleep 5; \
    done

# Create keys directory but don't generate keys during build
# Keys will be generated at runtime if they don't exist
RUN mkdir -p /app/keys

# Expose ports for FastAPI and Streamlit
EXPOSE 8000 8501

# Set environment variables
ENV PYTHONPATH=/app

# Make the start script executable
RUN chmod +x /app/start.sh

# Command to run the start script
CMD ["/app/start.sh"]
