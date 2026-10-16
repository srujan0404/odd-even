# Even or Odd

Small Flask app that tells you if a number is even or odd.

## Run

```
pip install -r app/requirements.txt
python -m app.app
```

Then open http://localhost:5000/check?number=10

```
{"even": true, "number": 10}
```

## Tests

```
pip install pytest
python -m pytest
```
