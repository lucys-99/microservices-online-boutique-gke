# Image Generation Service

The Image Generation Service is a new microservice that extends the Online Boutique application with AI-powered image generation capabilities. It uses Google's Gemini 2.5 Flash model to generate images of cart items with user-specified styles and background images.

## Features

- **Cart Integration**: Automatically fetches cart items and product details
- **AI Image Generation**: Uses Gemini 2.5 Flash to generate high-quality product images
- **Style Customization**: Supports multiple style preferences (modern, vintage, minimalist, etc.)
- **Background Upload**: Allows users to upload custom background images
- **Real-time Status**: Provides status tracking for image generation requests
- **Google Cloud Storage**: Stores generated images in GCS with public access

## Architecture

The service integrates with existing microservices:
- **Cart Service**: Retrieves user cart items
- **Product Catalog Service**: Gets detailed product information
- **Google Cloud Storage**: Stores generated images
- **Secret Manager**: Manages Gemini API keys securely

## API Endpoints

### GenerateCartImage
Generates an image of cart items with specified style and background.

**Request:**
```protobuf
message GenerateCartImageRequest {
    string user_id = 1;
    string style_preference = 2;  // "modern", "vintage", "minimalist", etc.
    string background_image_url = 3;  // Optional uploaded background
    repeated CartItem cart_items = 4;
}
```

**Response:**
```protobuf
message GenerateCartImageResponse {
    string image_url = 1;
    string generation_id = 2;
    string status = 3;  // "processing", "completed", "failed"
    string error_message = 4;
}
```

### UploadBackground
Uploads and processes a background image for use in image generation.

**Request:**
```protobuf
message UploadBackgroundRequest {
    string image_data = 1;  // Base64 encoded image data
}
```

**Response:**
```protobuf
message UploadBackgroundResponse {
    string image_url = 1;
    string status = 2;  // "success", "failed"
    string error_message = 3;
}
```

### GetImageGenerationStatus
Retrieves the status of an image generation request.

**Request:**
```protobuf
message GetStatusRequest {
    string generation_id = 1;
}
```

**Response:**
```protobuf
message GetStatusResponse {
    string status = 1;  // "processing", "completed", "failed", "not_found"
    string image_url = 2;
    int32 progress = 3;  // 0-100
    string error_message = 4;
}
```

## Environment Variables

- `PORT`: Service port (default: 8080)
- `CART_SERVICE_ADDR`: Cart service address (default: cartservice:7070)
- `PRODUCT_CATALOG_SERVICE_ADDR`: Product catalog service address (default: productcatalogservice:3550)
- `GCS_BUCKET`: Google Cloud Storage bucket name
- `PROJECT_ID`: Google Cloud project ID
- `GEMINI_API_KEY`: Gemini API key (can be from Secret Manager or env var)

## Deployment

### Using Helm
```bash
helm install online-boutique ./helm-chart \
  --set imageGenerationService.create=true \
  --set imageGenerationService.gcsBucket=your-bucket \
  --set imageGenerationService.projectId=your-project \
  --set imageGenerationService.geminiApiKey=your-api-key
```

### Using Kustomize
```bash
kubectl apply -k kustomize/components/image-generation
```

### Using Kubernetes Manifests
```bash
kubectl apply -f kubernetes-manifests/imagegenerationservice.yaml
```

## Prerequisites

1. **Google Cloud Project** with the following APIs enabled:
   - Generative AI API
   - Cloud Storage API
   - Secret Manager API

2. **Gemini API Key**: Obtain from Google AI Studio

3. **Google Cloud Storage Bucket**: Create a bucket for storing images

4. **Workload Identity**: Configure for secure access to Google Cloud services

## Development

### Local Development
```bash
# Install dependencies
pip install -r requirements.txt

# Set environment variables
export GEMINI_API_KEY=your-api-key
export GCS_BUCKET=your-bucket
export PROJECT_ID=your-project

# Run the service
python imagegenservice.py
```

### Building Docker Image
```bash
docker build -t gcr.io/PROJECT_ID/imagegenerationservice:latest .
docker push gcr.io/PROJECT_ID/imagegenerationservice:latest
```

## Integration with Frontend

The frontend can integrate with this service by:

1. Adding a "Generate Image" button to the cart view
2. Implementing background image upload functionality
3. Displaying generated images with download options
4. Showing real-time generation status

## Security Considerations

- API keys are stored in Secret Manager
- Workload Identity is used for secure GCS access
- Images are stored with appropriate access controls
- Input validation prevents malicious uploads

## Monitoring and Observability

- Health check endpoints (`/healthz`)
- Structured logging with request IDs
- Metrics for generation success/failure rates
- Integration with Google Cloud Operations Suite

## Future Enhancements

- Support for more AI models
- Batch image generation
- Advanced style transfer
- Image quality optimization
- Caching for frequently requested images
