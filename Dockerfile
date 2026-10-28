FROM python:3.11-slim
WORKDIR /app
# CPU-only torch first: keeps the image small (sentence-transformers needs it)
RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
# Hugging Face Spaces runs the container as uid 1000 and expects port 7860
RUN useradd -m -u 1000 user && chown -R user /app
USER user
ENV HF_HOME=/home/user/.cache
EXPOSE 7860
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "7860"]
