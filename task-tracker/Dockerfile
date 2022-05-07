FROM python:3.10
ENV SRC_PROJECT_PATH /app
RUN mkdir -p $SRC_PROJECT_PATH
WORKDIR $SRC_PROJECT_PATH
COPY requirements.txt $SRC_PROJECT_PATH
RUN pip install -r requirements.txt
COPY . $SRC_PROJECT_PATH
CMD ["uvicorn", "task_tracker.server:app", "--host", "0.0.0.0", "--reload"]
EXPOSE 8000
