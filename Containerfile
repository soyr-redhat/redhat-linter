# Use a lightweight Python image
FROM python:3.12-slim

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Set working directory
WORKDIR /app

# Copy dependency files first for better caching
COPY pyproject.toml uv.lock ./

# Install dependencies using uv
RUN uv sync --frozen

# Copy the rest of the application
COPY . .

# Ensure guides directory exists
RUN mkdir -p guides

# Expose Streamlit port
EXPOSE 8501

# Run the application
CMD ["uv", "run", "streamlit", "run", "app.py", "--server.address", "0.0.0.0"]
