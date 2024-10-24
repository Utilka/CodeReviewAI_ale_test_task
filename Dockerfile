FROM python:3.12

#COPY ./requirements.txt /requirements.txt
#RUN pip install --no-cache-dir --upgrade -r /requirements.txt
#COPY ./app /app
#
#CMD ["fastapi", "run", "/app/main.py", "--port", "80"]

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1
ENV PYTHONPATH="${PYTHONPATH}:/app"

# Install Poetry
RUN pip install --upgrade pip
RUN pip install poetry

# Copy Poetry files
COPY pyproject.toml poetry.lock /

# Install dependencies
RUN poetry config virtualenvs.create false
RUN poetry install --no-dev --no-interaction --no-ansi

# Copy project
COPY ./app /app

# Copy redme bcs poetry requires it
COPY ./README.md /

# Command to run the app
CMD ["bash"]
#CMD ["poetry", "run", "start"]