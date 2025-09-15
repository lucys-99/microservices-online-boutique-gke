#!/usr/bin/env python3
#
# Copyright 2024 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os
import uuid
import logging
import base64
import grpc
from concurrent import futures
from flask import Flask, request, jsonify
from google.cloud import storage, secretmanager_v1
from io import BytesIO
from PIL import Image

# Import Gemini (conditionally to support local development without the API)
try:
    import google.generativeai as genai
except ImportError:
    genai = None

# Import generated protobuf files
import demo_pb2
import demo_pb2_grpc

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ImageGenerationService(demo_pb2_grpc.ImageGenerationServiceServicer):
    def __init__(self):
        self.cart_service_addr = os.getenv('CART_SERVICE_ADDR', 'cartservice:7070')
        self.product_catalog_addr = os.getenv('PRODUCT_CATALOG_SERVICE_ADDR', 'productcatalogservice:3550')
        self.gcs_bucket = os.getenv('GCS_BUCKET', 'online-boutique-images')
        self.project_id = os.getenv('PROJECT_ID', 'your-project-id')
        
        # Initialize Google AI
        self._setup_gemini()
        
        # Initialize Google Cloud Storage
        self._setup_storage()
        
        # Initialize gRPC clients
        self._setup_grpc_clients()
        
        # In-memory storage for generation status (in production, use Redis or database)
        self.generation_status = {}

    def _setup_gemini(self):
        """Initialize Gemini AI client"""
        try:
            # Try to get API key from Secret Manager
            try:
                secret_client = secretmanager_v1.SecretManagerServiceClient()
                secret_name = f"projects/{self.project_id}/secrets/gemini-api-key/versions/latest"
                secret_response = secret_client.access_secret_version(request={"name": secret_name})
                api_key = secret_response.payload.data.decode("UTF-8").strip()
            except Exception as e:
                logger.warning(f"Failed to retrieve API key from Secret Manager: {e}")
                # Fallback to environment variable
                api_key = os.getenv('GEMINI_API_KEY')

            if api_key and genai:
                genai.configure(api_key=api_key)
                self.model = genai.GenerativeModel('gemini-2.0-flash-exp')
                logger.info("Gemini AI initialized successfully")
            else:
                logger.warning("No Gemini API key found or genai module not available")
                self.model = None
        except Exception as e:
            logger.error(f"Failed to initialize Gemini AI: {e}")
            self.model = None

    def _setup_storage(self):
        """Initialize Google Cloud Storage client"""
        try:
            self.storage_client = storage.Client(project=self.project_id)
            self.bucket = self.storage_client.bucket(self.gcs_bucket)
            logger.info(f"Google Cloud Storage initialized with bucket: {self.gcs_bucket}")
        except Exception as e:
            logger.error(f"Failed to initialize Google Cloud Storage: {e}")
            # For local development, we'll use a mock
            self.storage_client = None
            self.bucket = None

    def _setup_grpc_clients(self):
        """Initialize gRPC clients for cart and product services"""
        try:
            # Cart service client
            self.cart_channel = grpc.insecure_channel(self.cart_service_addr)
            self.cart_stub = demo_pb2_grpc.CartServiceStub(self.cart_channel)
            
            # Product catalog client
            self.product_channel = grpc.insecure_channel(self.product_catalog_addr)
            self.product_stub = demo_pb2_grpc.ProductCatalogServiceStub(self.product_channel)
            
            logger.info("gRPC clients initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize gRPC clients: {e}")
            # For local development without other services
            from grpc_stubs import CartServiceStub, ProductCatalogServiceStub
            self.cart_stub = CartServiceStub(None)
            self.product_stub = ProductCatalogServiceStub(None)
            logger.info("Using stub implementations for local development")

    def GenerateCartImage(self, request, context):
        """Generate an image of cart items with specified style and background"""
        try:
            generation_id = str(uuid.uuid4())
            logger.info(f"Starting image generation for user {request.user_id}, generation_id: {generation_id}")
            
            # Update status to processing
            self.generation_status[generation_id] = {
                'status': 'processing',
                'user_id': request.user_id,
                'progress': 0
            }
            
            # Get cart items
            cart_items = request.cart_items
            if not cart_items and request.user_id:
                cart_items = self._get_cart_items(request.user_id)
            
            if not cart_items:
                logger.warning(f"No cart items found for user {request.user_id}")
                return demo_pb2.GenerateCartImageResponse(
                    generation_id=generation_id,
                    status="failed",
                    error_message="No items found in cart"
                )
            
            # Get product details
            product_details = self._get_product_details(cart_items)
            
            # Generate image
            image_url = self._generate_image_with_gemini(
                product_details, 
                request.style_preference, 
                request.background_image_url,
                generation_id
            )
            
            # Update status to completed
            self.generation_status[generation_id] = {
                'status': 'completed',
                'user_id': request.user_id,
                'image_url': image_url,
                'progress': 100
            }
            
            return demo_pb2.GenerateCartImageResponse(
                image_url=image_url,
                generation_id=generation_id,
                status="completed"
            )
            
        except Exception as e:
            logger.error(f"Error generating cart image: {e}")
            if generation_id:
                self.generation_status[generation_id] = {
                    'status': 'failed',
                    'user_id': request.user_id,
                    'error_message': str(e)
                }
            return demo_pb2.GenerateCartImageResponse(
                generation_id=generation_id if 'generation_id' in locals() else str(uuid.uuid4()),
                status="failed",
                error_message=str(e)
            )

    def UploadBackground(self, request, context):
        """Upload and process background image"""
        try:
            # Decode base64 image
            image_data = base64.b64decode(request.image_data)
            
            # Validate and process image
            image = Image.open(BytesIO(image_data))
            
            # Resize if too large
            max_size = (1920, 1080)
            if image.size[0] > max_size[0] or image.size[1] > max_size[1]:
                image.thumbnail(max_size, Image.LANCZOS)
            
            # Convert to RGB if necessary
            if image.mode != 'RGB':
                image = image.convert('RGB')
            
            # If we have storage access
            if self.bucket:
                # Upload to GCS
                filename = f"backgrounds/{str(uuid.uuid4())}.jpg"
                blob = self.bucket.blob(filename)
                
                # Save processed image to bytes
                img_byte_arr = BytesIO()
                image.save(img_byte_arr, format='JPEG', quality=85)
                img_byte_arr = img_byte_arr.getvalue()
                
                # Upload to GCS
                blob.upload_from_string(img_byte_arr, content_type='image/jpeg')
                
                # Make blob publicly accessible
                blob.make_public()
                
                image_url = blob.public_url
            else:
                # Local development mode - mock URL
                image_url = f"https://storage.googleapis.com/{self.gcs_bucket}/mock-background-{uuid.uuid4()}.jpg"
                
            logger.info(f"Background image uploaded: {image_url}")
            
            return demo_pb2.UploadBackgroundResponse(
                image_url=image_url,
                status="success"
            )
            
        except Exception as e:
            logger.error(f"Error uploading background image: {e}")
            return demo_pb2.UploadBackgroundResponse(
                status="failed",
                error_message=str(e)
            )

    def GetImageGenerationStatus(self, request, context):
        """Get the status of an image generation request"""
        try:
            status_info = self.generation_status.get(request.generation_id)
            if not status_info:
                return demo_pb2.GetStatusResponse(
                    status="not_found",
                    error_message=f"Generation ID {request.generation_id} not found"
                )
            
            return demo_pb2.GetStatusResponse(
                status=status_info['status'],
                image_url=status_info.get('image_url', ''),
                progress=status_info.get('progress', 0),
                error_message=status_info.get('error_message', '')
            )
            
        except Exception as e:
            logger.error(f"Error getting generation status: {e}")
            return demo_pb2.GetStatusResponse(
                status="error",
                error_message=str(e)
            )

    def _get_cart_items(self, user_id):
        """Get cart items for a user"""
        try:
            cart_request = demo_pb2.GetCartRequest(user_id=user_id)
            cart_response = self.cart_stub.GetCart(cart_request)
            return cart_response.items
        except Exception as e:
            logger.error(f"Error getting cart items: {e}")
            return []

    def _get_product_details(self, cart_items):
        """Get detailed product information for cart items"""
        product_details = []
        for item in cart_items:
            try:
                product_request = demo_pb2.GetProductRequest(id=item.product_id)
                product = self.product_stub.GetProduct(product_request)
                product_details.append({
                    'id': product.id,
                    'name': product.name,
                    'description': product.description,
                    'picture': product.picture,
                    'quantity': item.quantity
                })
            except Exception as e:
                logger.error(f"Error getting product details for {item.product_id}: {e}")
                
        return product_details

    def _generate_image_with_gemini(self, product_details, style_preference, background_url, generation_id):
        """Generate image using Gemini 2.5 Flash"""
        try:
            # Update progress
            self.generation_status[generation_id]['progress'] = 25
            
            # Create product description
            products_text = self._create_product_description(product_details)
            
            # Create style-specific prompt
            style_prompt = self._create_style_prompt(style_preference)
            
            # For actual Gemini integration
            if self.model:
                prompt = f"""
                Generate a realistic product image showing the following items in a {style_preference} style:
                {products_text}
                
                Style instructions: {style_prompt}
                
                Background: {'Use the provided background image as context.' if background_url else 'Use a clean, appropriate background that highlights the products.'}
                
                Make it look like a professional product photography with good lighting and composition.
                """
                
                # Update progress
                self.generation_status[generation_id]['progress'] = 50
                
                # Call Gemini API here
                # response = self.model.generate_content(prompt)
                # For demo we'll return a mock URL
                
                # Update progress
                self.generation_status[generation_id]['progress'] = 100
                
                # In production, you would save the generated image and return its URL
                return self._create_placeholder_image(product_details, style_preference, generation_id)
            else:
                # Local development mode without Gemini
                return self._create_placeholder_image(product_details, style_preference, generation_id)
            
        except Exception as e:
            logger.error(f"Error generating image with Gemini: {e}")
            return self._create_placeholder_image(product_details, style_preference, generation_id)
        # return self._create_placeholder_image(product_details, style_preference, generation_id)

    def _create_product_description(self, product_details):
        """Create a text description of products for the AI prompt"""
        description = ""
        for product in product_details:
            description += f"- {product.get('name', 'Unknown product')} ({product.get('quantity', 1)}x): {product.get('description', 'No description')}\n"
        return description

    def _create_style_prompt(self, style_preference):
        """Create style-specific prompt based on user preference"""
        style_prompts = {
            'modern': "Modern, clean, minimalist aesthetic with contemporary styling and sleek presentation",
            'vintage': "Vintage-inspired styling with classic, timeless appeal and warm, nostalgic tones",
            'minimalist': "Ultra-clean, minimalist composition with focus on simplicity and negative space",
            'luxury': "High-end, luxurious presentation with premium materials and sophisticated styling",
            'casual': "Relaxed, casual styling with comfortable, everyday appeal",
            'professional': "Professional, business-appropriate styling suitable for corporate environments"
        }
        
        return style_prompts.get(style_preference.lower(), style_prompts['modern'])

    def _create_placeholder_image(self, product_details, style_preference, generation_id):
        """Create a placeholder image (in production, this would be the actual generated image)"""
        import random
        try:
            # List of sample product images for debugging
            random_images = [
                "https://picsum.photos/600/400?random=1",  # Random image from Lorem Picsum
                "https://picsum.photos/600/400?random=2", 
                "https://picsum.photos/600/400?random=3",
                "https://source.unsplash.com/600x400/?product",  # Random product from Unsplash
                "https://source.unsplash.com/600x400/?retail",   # Random retail image from Unsplash
                f"https://placehold.co/600x400/random/white?text=Debug+Image+{generation_id[:6]}",
            ]
            
            # Use style preference to modify selection
            if style_preference and style_preference.lower() in ['vintage', 'modern', 'minimalist', 'luxury']:
                style_images = {
                    'vintage': "https://source.unsplash.com/600x400/?vintage",
                    'modern': "https://source.unsplash.com/600x400/?modern",
                    'minimalist': "https://source.unsplash.com/600x400/?minimalist",
                    'luxury': "https://source.unsplash.com/600x400/?luxury"
                }
                random_images.append(style_images[style_preference.lower()])
            
            selected_image = random.choice(random_images)
            logger.info(f"🔍 DEBUG: Selected random debug image: {selected_image}")
            
            # Extract product names for debugging
            product_names = []
            try:
                for product in product_details:
                    product_names.append(f"{product.get('name', 'Unknown')} ({product.get('quantity', 1)}x)")
                logger.info(f"🔍 DEBUG: Would generate image for products: {', '.join(product_names)}")
            except:
                logger.info("🔍 DEBUG: No valid product details to display")
            
            return selected_image
        except Exception as e:
            logger.error(f"🔍 DEBUG: Error creating placeholder image: {e}")
            return f"https://placehold.co/600x400?text=Error+{generation_id[:6]}"

# For MCP/A2A integration (optional)
class MCPAdapter:
    def __init__(self, image_gen_service):
        self.image_gen_service = image_gen_service
        self.app = Flask(__name__)
        self.setup_routes()
        
    def setup_routes(self):
        @self.app.route('/mcp', methods=['POST'])
        def mcp_handler():
            mcp_request = request.json
            if mcp_request["action"] == "generate_image":
                # Transform MCP request to gRPC request
                grpc_request = demo_pb2.GenerateCartImageRequest(
                    user_id=mcp_request["params"].get("user_id", ""),
                    style_preference=mcp_request["params"].get("style", "modern"),
                    background_image_url=mcp_request["params"].get("background_url", "")
                )
                # Call the service
                result = self.image_gen_service.GenerateCartImage(grpc_request, None)
                return jsonify({"result": {
                    "image_url": result.image_url,
                    "generation_id": result.generation_id,
                    "status": result.status
                }, "status": "success"})
            return jsonify({"status": "error", "message": "Unknown action"})
        
        @self.app.route('/a2a', methods=['POST'])
        def a2a_handler():
            a2a_request = request.json
            if a2a_request["method"] == "generate_image":
                # Transform A2A request to gRPC request
                grpc_request = demo_pb2.GenerateCartImageRequest(
                    user_id=a2a_request["params"].get("user_id", ""),
                    style_preference=a2a_request["params"].get("style", "modern"),
                    background_image_url=a2a_request["params"].get("background_url", "")
                )
                # Call the service
                result = self.image_gen_service.GenerateCartImage(grpc_request, None)
                return jsonify({"result": {
                    "image_url": result.image_url,
                    "generation_id": result.generation_id,
                    "status": result.status
                }, "status": "success"})
            return jsonify({"status": "error", "message": "Unknown method"})
    
    def run(self, host='0.0.0.0', port=8080):
        self.app.run(host=host, port=port)

def serve():
    """Start the gRPC server"""
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    service = ImageGenerationService()
    demo_pb2_grpc.add_ImageGenerationServiceServicer_to_server(service, server)
    
    port = os.getenv('PORT', '9100')
    server.add_insecure_port(f'[::]:{port}')
    
    logger.info(f"Starting ImageGenerationService on port {port}")
    server.start()
    
    # Optionally start MCP/A2A adapter on a different port
    # Uncomment to enable
    # mcp_port = int(port) + 1
    # mcp_adapter = MCPAdapter(service)
    # thread = threading.Thread(target=mcp_adapter.run, kwargs={'port': mcp_port})
    # thread.daemon = True
    # thread.start()
    # logger.info(f"MCP/A2A adapter started on port {mcp_port}")
    
    server.wait_for_termination()

if __name__ == '__main__':
    serve()
