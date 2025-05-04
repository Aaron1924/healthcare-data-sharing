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

# Install Node.js dependencies
RUN cd /app && npm install

# Compile the smart contract
RUN cd /app && npm run compile

# Expose ports for FastAPI and Streamlit
EXPOSE 8000 8501

# Set environment variables
ENV PYTHONPATH=/app

# Command will be overridden by docker-compose
CMD ["echo", "This command will be overridden by docker-compose"]
