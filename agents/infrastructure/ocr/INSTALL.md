# DeepSeek-OCR Service Installation Guide

## Prerequisites

This service uses Tesseract OCR as a fallback until the full Deep

Seek-OCR model is available.

## Step 1: Install System Dependencies (Requires sudo)

```bash
# Install Tesseract OCR
sudo apt-get update
sudo apt-get install -y tesseract-ocr tesseract-ocr-eng libtesseract-dev

# Verify installation
tesseract --version
```

## Step 2: Install Python Dependencies (Already done)

```bash
pip install flask pytesseract pillow redis requests
```

## Step 3: Test OCR Service Locally

```bash
# Start service
cd /home/genesis/genesis-rebuild
python infrastructure/ocr/deepseek_ocr_service.py

# Service will run on http://localhost:8001
```

## Step 4: Test with Sample Image

```bash
# In another terminal
curl http://localhost:8001/health

# Should return:
# {
#   "status": "healthy",
#   "model_loaded": false,
#   "cache_enabled": true,
#   "engine": "tesseract"
# }
```

## Step 5: Build Docker Image (Optional, after Tesseract installed)

```bash
docker build -t genesis-deepseek-ocr:latest -f infrastructure/docker/deepseek-ocr-cpu.Dockerfile .
```

## Step 6: Run with Docker Compose

```bash
docker compose up -d deepseek-ocr
docker compose logs -f deepseek-ocr
```

## Troubleshooting

### Issue: "tesseract: command not found"

**Solution:** Run Step 1 (install Tesseract)

### Issue: Docker build hangs

**Solution:** Build may take 5-10 minutes due to package downloads. Check:

```bash
docker build --progress=plain -t genesis-deepseek-ocr:latest -f infrastructure/docker/deepseek-ocr-cpu.Dockerfile .
```

### Issue: Import error for pytesseract

**Solution:**

```bash
pip install pytesseract pillow
```

## Performance Notes

- **CPU Inference:** 2-3x slower than GPU (120-180s per image vs. 58s)
- **Caching:** Repeated images use cache (<1s response)
- **Batch Processing:** Process multiple images sequentially
- **Optimization:** AMD EPYC processor supports multi-threading

## Next Steps

1. Install Tesseract (Step 1)
2. Test service locally (Step 3-4)
3. Create test images
4. Integrate with agents
