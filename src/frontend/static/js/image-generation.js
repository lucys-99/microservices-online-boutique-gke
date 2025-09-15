/**
 * Copyright 2024 Google LLC
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *      https://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

// Global variables
let currentGenerationId = null;
let uploadedBackgroundUrl = null;
let uploadedBackgroundData = null;

// Modal functions
function openImageGenerationModal() {
    const modal = document.getElementById('imageGenerationModal');
    modal.style.display = 'block';
    document.body.style.overflow = 'hidden';
    
    // Reset form
    resetImageGenerationForm();
}

function closeImageGenerationModal() {
    const modal = document.getElementById('imageGenerationModal');
    modal.style.display = 'none';
    document.body.style.overflow = 'auto';
    
    // Reset form
    resetImageGenerationForm();
}

function resetImageGenerationForm() {
    // Reset form elements
    document.getElementById('stylePreference').value = 'modern';
    document.getElementById('backgroundUpload').value = '';
    
    // Hide all sections
    document.getElementById('generationProgress').style.display = 'none';
    document.getElementById('generatedImageResult').style.display = 'none';
    
    // Show form
    document.querySelector('.image-generation-form').style.display = 'block';
    
    // Reset background preview
    removeBackground();
    
    // Reset variables
    currentGenerationId = null;
    uploadedBackgroundUrl = null;
    uploadedBackgroundData = null;
}

// Background upload functions
function handleBackgroundUpload(event) {
    const file = event.target.files[0];
    if (!file) return;
    
    // Validate file type
    if (!file.type.startsWith('image/')) {
        alert('Please select an image file.');
        return;
    }
    
    // Validate file size (max 10MB)
    if (file.size > 10 * 1024 * 1024) {
        alert('File size must be less than 10MB.');
        return;
    }
    
    // Convert to base64
    const reader = new FileReader();
    reader.onload = function(e) {
        uploadedBackgroundData = e.target.result.split(',')[1]; // Remove data:image/...;base64, prefix
        
        // Show preview
        showBackgroundPreview(e.target.result);
        
        // Upload to server
        uploadBackgroundToServer();
    };
    reader.readAsDataURL(file);
}

function showBackgroundPreview(imageData) {
    const preview = document.getElementById('backgroundPreview');
    const previewImg = document.getElementById('backgroundPreviewImg');
    const placeholder = document.getElementById('backgroundPlaceholder');
    
    previewImg.src = imageData;
    preview.style.display = 'block';
    placeholder.style.display = 'none';
}

function removeBackground() {
    const preview = document.getElementById('backgroundPreview');
    const placeholder = document.getElementById('backgroundPlaceholder');
    const fileInput = document.getElementById('backgroundUpload');
    
    preview.style.display = 'none';
    placeholder.style.display = 'block';
    fileInput.value = '';
    
    uploadedBackgroundUrl = null;
    uploadedBackgroundData = null;
}

async function uploadBackgroundToServer() {
    try {
        const response = await fetch('/api/v1/upload-background', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                image_data: uploadedBackgroundData
            })
        });
        
        const result = await response.json();
        
        if (result.status === 'success') {
            uploadedBackgroundUrl = result.image_url;
            console.log('Background uploaded successfully:', result.image_url);
        } else {
            console.error('Background upload failed:', result.error_message);
            alert('Failed to upload background image. Please try again.');
            removeBackground();
        }
    } catch (error) {
        console.error('Error uploading background:', error);
        alert('Error uploading background image. Please try again.');
        removeBackground();
    }
}

// Image generation functions
async function generateImage() {
    console.log("🔍 DEBUG: Generate Image button clicked");
    const stylePreference = document.getElementById('stylePreference').value;
    console.log("🔍 DEBUG: Style preference:", stylePreference);
    
    // Get cart items from the page
    const cartItems = getCartItemsFromPage();
    console.log("🔍 DEBUG: Cart items:", cartItems);
    
    if (cartItems.length === 0) {
        alert('Your cart is empty. Please add some items before generating an image.');
        return;
    }
    
    // Show progress section
    showGenerationProgress();
    console.log("🔍 DEBUG: Showing progress indicator");
    
    const requestData = {
        user_id: getCurrentUserId(),
        style_preference: stylePreference,
        background_image_url: uploadedBackgroundUrl || '',
        cart_items: cartItems
    };
    console.log("🔍 DEBUG: Request data:", JSON.stringify(requestData, null, 2));
    
    try {
        console.log("🔍 DEBUG: Sending fetch request to /api/v1/generate-image");
        const startTime = performance.now();
        
        const response = await fetch('/api/v1/generate-image', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(requestData)
        });
        
        const endTime = performance.now();
        console.log(`🔍 DEBUG: Request took ${Math.round(endTime - startTime)}ms`);
        console.log("🔍 DEBUG: Response status:", response.status);
        
        const result = await response.json();
        console.log("🔍 DEBUG: Response data:", result);
        
        if (result.status === 'completed') {
            currentGenerationId = result.generation_id;
            showGeneratedImage(result.image_url);
        } else if (result.status === 'processing') {
            currentGenerationId = result.generation_id;
            pollGenerationStatus();
        } else {
            throw new Error(result.error_message || 'Image generation failed');
        }
    } catch (error) {
        console.error('Error generating image:', error);
        alert('Error generating image: ' + error.message);
        resetImageGenerationForm();
    }
}

function getCartItemsFromPage() {
    const cartItems = [];
    const itemRows = document.querySelectorAll('.cart-summary-item-row');
    
    itemRows.forEach(row => {
        const productLink = row.querySelector('a[href*="/product/"]');
        if (productLink) {
            const productId = productLink.href.split('/product/')[1];
            const quantityElement = row.querySelector('.col:contains("Quantity:")');
            const quantity = quantityElement ? parseInt(quantityElement.textContent.match(/\d+/)[0]) : 1;
            
            cartItems.push({
                product_id: productId,
                quantity: quantity
            });
        }
    });
    
    return cartItems;
}

function getCurrentUserId() {
    // In a real implementation, this would come from the session
    // For now, we'll use a placeholder
    return 'user_' + Date.now();
}

function showGenerationProgress() {
    document.querySelector('.image-generation-form').style.display = 'none';
    document.getElementById('generationProgress').style.display = 'block';
    document.getElementById('generatedImageResult').style.display = 'none';
    
    // Reset progress
    updateProgress(0);
}

function updateProgress(percentage) {
    const progressBar = document.getElementById('progressBar');
    const progressText = document.getElementById('progressText');
    
    progressBar.style.width = percentage + '%';
    progressText.textContent = percentage + '%';
}

async function pollGenerationStatus() {
    if (!currentGenerationId) return;
    
    try {
        const response = await fetch(`/api/v1/status/${currentGenerationId}`);
        const result = await response.json();
        
        updateProgress(result.progress || 0);
        
        if (result.status === 'completed') {
            showGeneratedImage(result.image_url);
        } else if (result.status === 'failed') {
            throw new Error(result.error_message || 'Image generation failed');
        } else if (result.status === 'processing') {
            // Continue polling
            setTimeout(pollGenerationStatus, 2000);
        }
    } catch (error) {
        console.error('Error polling status:', error);
        alert('Error checking generation status: ' + error.message);
        resetImageGenerationForm();
    }
}

function showGeneratedImage(imageUrl) {
    console.log("🔍 DEBUG: Showing generated image:", imageUrl);
    document.getElementById('generationProgress').style.display = 'none';
    document.getElementById('generatedImageResult').style.display = 'block';
    
    const generatedImage = document.getElementById('generatedImage');
    generatedImage.src = imageUrl;
    generatedImage.onload = function() {
        // Image loaded successfully
        console.log('🔍 DEBUG: Image dimensions:', generatedImage.naturalWidth, 'x', generatedImage.naturalHeight);
    };
    generatedImage.onerror = function() {
        console.error('🔍 DEBUG: Failed to load image from URL:', imageUrl);
        alert('Failed to load generated image. Please try again.');
        resetImageGenerationForm();
    };
}

function downloadImage() {
    const generatedImage = document.getElementById('generatedImage');
    const imageUrl = generatedImage.src;
    
    if (!imageUrl) {
        alert('No image to download.');
        return;
    }
    
    // Create a temporary link to download the image
    const link = document.createElement('a');
    link.href = imageUrl;
    link.download = `cart-image-${currentGenerationId || Date.now()}.jpg`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
}

// Close modal when clicking outside
window.onclick = function(event) {
    const modal = document.getElementById('imageGenerationModal');
    if (event.target === modal) {
        closeImageGenerationModal();
    }
}

// Close modal with Escape key
document.addEventListener('keydown', function(event) {
    if (event.key === 'Escape') {
        const modal = document.getElementById('imageGenerationModal');
        if (modal.style.display === 'block') {
            closeImageGenerationModal();
        }
    }
});
