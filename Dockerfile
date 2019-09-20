from python:3-alpine
RUN pip install --quiet flake8 coverage
COPY . /app
WORKDIR /app
ENV TZ=UTC
CMD python balance.py --split make_balance


