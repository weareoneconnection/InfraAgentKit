FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt pyproject.toml README.md ./
COPY infraagentkit ./infraagentkit
RUN pip install --no-cache-dir -r requirements.txt && pip install --no-cache-dir -e .
COPY . .
ENV INFRAAGENTKIT_DB=/data/infraagentkit.db
EXPOSE 8103
CMD ["python", "-m", "infraagentkit.cli", "serve", "--host", "0.0.0.0", "--port", "8103"]
