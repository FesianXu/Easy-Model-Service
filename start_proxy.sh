#!/bin/bash

uvicorn proxy:app --host 0.0.0.0 --port 8000 --workers 1