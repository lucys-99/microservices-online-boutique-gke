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

from flask import Flask, request, jsonify
import base64
import logging
import os
from imagegenerationservice.imagegenservice import ImageGenerationService
import demo_pb2

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Initialize the gRPC service
grpc_service = ImageGenerationService()

@app.route('/healthz', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({"status": "healthy"}), 200

@app.route('/api/v1/generate-image', methods=['POST'])
def generate_image():
    """HTTP endpoint for generating cart images"""
    logger.info("🔍 DEBUG: /api/v1/generate-image endpoint called")
    try:
        data = request.get_json()
        logger.info(f"🔍 DEBUG: Request data: {data}")
        
        # Create gRPC request
        grpc_request = demo_pb2.GenerateCartImageRequest()
        grpc_request.user_id = data.get('user_id', '')
        grpc_request.style_preference = data.get('style_preference', 'modern')
        grpc_request.background_image_url = data.get('background_image_url', '')
        
        logger.info(f"🔍 DEBUG: User ID: {grpc_request.user_id}")
        logger.info(f"🔍 DEBUG: Style preference: {grpc_request.style_preference}")
        logger.info(f"🔍 DEBUG: Background URL: {grpc_request.background_image_url}")
        
        # Add cart items if provided
        if 'cart_items' in data:
            cart_item_count = 0
            for item_data in data['cart_items']:
                cart_item = demo_pb2.CartItem()
                cart_item.product_id = item_data.get('product_id', '')
                cart_item.quantity = item_data.get('quantity', 1)
                grpc_request.cart_items.append(cart_item)
                cart_item_count += 1
            logger.info(f"🔍 DEBUG: Added {cart_item_count} cart items to request")
        else:
            logger.warning("🔍 DEBUG: No cart items in request")
        
        # Call gRPC service
        logger.info("🔍 DEBUG: Calling GenerateCartImage gRPC method")
        import time
        start_time = time.time()
        
        response = grpc_service.GenerateCartImage(grpc_request, None)
        
        end_time = time.time()
        logger.info(f"🔍 DEBUG: gRPC call took {(end_time - start_time)*1000:.2f}ms")
        logger.info(f"🔍 DEBUG: Response - status: {response.status}, image URL: {response.image_url}")
        
        result = {
            'image_url': response.image_url,
            'generation_id': response.generation_id,
            'status': response.status,
            'error_message': response.error_message
        }
        logger.info("🔍 DEBUG: Returning successful response to client")
        return jsonify(result), 200
        
    except Exception as e:
        logger.error(f"🔍 DEBUG: Error in generate_image: {e}")
        import traceback
        logger.error(f"🔍 DEBUG: Traceback: {traceback.format_exc()}")
        return jsonify({
            'error': str(e),
            'status': 'failed'
        }), 500

@app.route('/api/v1/upload-background', methods=['POST'])
def upload_background():
    """HTTP endpoint for uploading background images"""
    try:
        data = request.get_json()
        
        # Create gRPC request
        grpc_request = demo_pb2.UploadBackgroundRequest()
        grpc_request.image_data = data.get('image_data', '')
        
        # Call gRPC service
        response = grpc_service.UploadBackground(grpc_request, None)
        
        return jsonify({
            'image_url': response.image_url,
            'status': response.status,
            'error_message': response.error_message
        }), 200
        
    except Exception as e:
        logger.error(f"Error in upload_background: {e}")
        return jsonify({
            'error': str(e),
            'status': 'failed'
        }), 500

@app.route('/api/v1/status/<generation_id>', methods=['GET'])
def get_status(generation_id):
    """HTTP endpoint for getting generation status"""
    try:
        # Create gRPC request
        grpc_request = demo_pb2.GetStatusRequest()
        grpc_request.generation_id = generation_id
        
        # Call gRPC service
        response = grpc_service.GetImageGenerationStatus(grpc_request, None)
        
        return jsonify({
            'status': response.status,
            'image_url': response.image_url,
            'progress': response.progress,
            'error_message': response.error_message
        }), 200
        
    except Exception as e:
        logger.error(f"Error in get_status: {e}")
        return jsonify({
            'error': str(e),
            'status': 'error'
        }), 500

if __name__ == '__main__':
    port = int(os.getenv('HTTP_PORT', '9100'))
    app.run(host='0.0.0.0', port=port, debug=False)
