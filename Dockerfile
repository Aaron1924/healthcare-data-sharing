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
    && rm -rf /var/lib/apt/lists/*

# Clone and build MCL library
RUN git clone https://github.com/herumi/mcl.git && \
    cd mcl && \
    cmake -B build . && \
    make -C build && \
    cd ..

# Set MCL_LIB_PATH environment variable
ENV MCL_LIB_PATH=/app/mcl/build/lib

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

# Command to run when the container starts
CMD ["sh", "-c", "python -m uvicorn backend.api:app --host 0.0.0.0 --port 8000 & streamlit run app/main.py"]
