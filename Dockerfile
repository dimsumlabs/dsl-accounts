from python:2
RUN pip install --quiet flake8 coverage
COPY . /app
WORKDIR /app
CMD python balance.py --split make_balance


