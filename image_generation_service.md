# Image Generation Service

This document describes the AI-powered image generation functionality in the Online Boutique application.

## Overview

The frontend has been enhanced with a comprehensive image generation interface that allows users to:
- Generate AI-powered images of their cart items
- Upload custom background images
- Select from various style preferences
- Track generation progress in real-time
- Download generated images

## Components Added

### 1. Cart Page Enhancement (`templates/cart.html`)
- **Generate Image Button**: Added to the cart header for easy access
- **Image Generation Modal**: Complete modal interface with form controls
- **Style Selection**: Dropdown for choosing image style (modern, vintage, minimalist, etc.)
- **Background Upload**: File upload with preview functionality
- **Progress Tracking**: Real-time progress bar and status updates
- **Result Display**: Generated image display with download option

### 2. CSS Styling (`static/styles/image-generation.css`)
- **Modal Styles**: Professional modal design with animations
- **Form Controls**: Styled form elements and file upload areas
- **Progress Indicators**: Visual progress bars and loading states
- **Responsive Design**: Mobile-friendly layout
- **Button Styles**: Consistent with existing design system

### 3. JavaScript Functionality (`static/js/image-generation.js`)
- **Modal Management**: Open/close modal with keyboard and click handlers
- **File Upload**: Background image upload with validation and preview
- **API Integration**: Communication with image generation service
- **Progress Polling**: Real-time status updates during generation
- **Error Handling**: Comprehensive error handling and user feedback

### 4. Backend Integration (`handlers.go`)
- **API Proxies**: HTTP handlers that forward requests to image generation service
- **Request/Response Handling**: JSON serialization and error handling
- **Service Discovery**: Integration with image generation service

## API Endpoints

The frontend exposes the following API endpoints:

### POST `/api/v1/generate-image`
Generates an image of cart items with specified style and background.

**Request Body:**
```json
{
  "user_id": "string",
  "style_preference": "modern|vintage|minimalist|luxury|casual|professional",
  "background_image_url": "string",
  "cart_items": [
    {
      "product_id": "string",
      "quantity": 1
    }
  ]
}
```

**Response:**
```json
{
  "image_url": "string",
  "generation_id": "string",
  "status": "processing|completed|failed",
  "error_message": "string"
}
```

### POST `/api/v1/upload-background`
Uploads a background image for use in image generation.

**Request Body:**
```json
{
  "image_data": "base64-encoded-image-data"
}
```

**Response:**
```json
{
  "image_url": "string",
  "status": "success|failed",
  "error_message": "string"
}
```

### GET `/api/v1/status/{generation_id}`
Gets the status of an image generation request.

**Response:**
```json
{
  "status": "processing|completed|failed|not_found",
  "image_url": "string",
  "progress": 0-100,
  "error_message": "string"
}
```

## User Experience Flow

1. **Access**: User clicks "Generate Image" button in cart
2. **Configuration**: User selects style preference and optionally uploads background
3. **Generation**: System generates image using AI with real-time progress updates
4. **Result**: Generated image is displayed with download option
5. **Download**: User can download the generated image

## Technical Implementation

### Frontend Architecture
- **Template Integration**: Seamlessly integrated into existing cart template
- **CSS Framework**: Uses existing Bootstrap classes with custom styling
- **JavaScript**: Vanilla JavaScript with modern ES6+ features
- **API Communication**: RESTful API calls with proper error handling

### Backend Integration
- **Service Proxy**: Frontend acts as proxy to image generation service
- **Environment Configuration**: Service address configured via environment variables
- **Error Handling**: Comprehensive error handling and logging
- **Request Forwarding**: Clean separation between frontend and image generation service

### Security Considerations
- **File Validation**: Image file type and size validation
- **Input Sanitization**: Proper input validation and sanitization
- **Error Messages**: Safe error messages without sensitive information
- **CORS Handling**: Proper cross-origin request handling

## Configuration

### Environment Variables
The frontend requires the following environment variable:
- `IMAGE_GENERATION_SERVICE_ADDR`: Address of the image generation service (default: `imagegenerationservice:8081`)

### Service Dependencies
- Image Generation Service must be deployed and accessible
- Google Cloud Storage bucket for image storage
- Gemini API access for AI image generation

## Deployment

### Kubernetes
The frontend deployment automatically includes the image generation functionality when the image generation service is deployed.

### Helm
```bash
helm install online-boutique ./helm-chart \
  --set imageGenerationService.create=true \
  --set imageGenerationService.gcsBucket=your-bucket \
  --set imageGenerationService.projectId=your-project \
  --set imageGenerationService.geminiApiKey=your-api-key
```

### Kustomize
```bash
kubectl apply -k kustomize/components/image-generation
```

## Testing

### Manual Testing
1. Add items to cart
2. Click "Generate Image" button
3. Select style preference
4. Optionally upload background image
5. Click "Generate Image"
6. Monitor progress and view result
7. Download generated image

### Automated Testing
The frontend includes comprehensive error handling and validation that can be tested with various scenarios:
- Empty cart generation
- Invalid file uploads
- Network errors
- Service unavailability


## Performance Considerations

- **Lazy Loading**: Images are loaded only when needed
- **Progress Updates**: Efficient polling with reasonable intervals
- **File Size Limits**: Background images limited to 10MB
- **Caching**: Generated images cached in Google Cloud Storage
- **Responsive Design**: Optimized for various screen sizes

## Future Enhancements

- **Batch Generation**: Generate multiple images with different styles
- **Image Editing**: Basic editing capabilities for generated images
- **Social Sharing**: Share generated images on social media
- **History**: View previously generated images
- **Advanced Styles**: More style options and custom prompts
- **Real-time Collaboration**: Share generation process with others

## Troubleshooting

### Common Issues
1. **Service Unavailable**: Check if image generation service is running
2. **Upload Failures**: Verify file size and format requirements
3. **Generation Timeout**: Check Gemini API limits and quotas
4. **Image Not Loading**: Verify Google Cloud Storage permissions

