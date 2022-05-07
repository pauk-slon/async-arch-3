FROM python:3.10 as base
ENV SRC_PROJECT_PATH /app
RUN mkdir -p $SRC_PROJECT_PATH
WORKDIR $SRC_PROJECT_PATH
COPY requirements.txt $SRC_PROJECT_PATH
RUN pip install -r requirements.txt
COPY . $SRC_PROJECT_PATH

FROM base as web-server
CMD ["uvicorn", "task_tracker.web_server:app", "--host", "0.0.0.0", "--reload"]
EXPOSE 8000

FROM base as event-consumer
CMD ["python", "-m", "task_tracker.event_streaming"]
