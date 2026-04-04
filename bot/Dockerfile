FROM python:3.12-slim
WORKDIR /app
COPY pyproject.toml /app/
COPY tg_bot /app/tg_bot
RUN pip install --no-cache-dir .
CMD ["python", "-m", "tg_bot.main"]
