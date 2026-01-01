# Google Cloud Storage Setup for Salon Platform

## Overview
The salon platform uses Google Cloud Storage (GCS) for storing uploaded salon logos and other files. This document explains how to set up GCS for local development and production.

## Prerequisites
- Google Cloud Platform account
- Project created in GCP Console
- `google-cloud-storage` Python package (already in requirements)

## Setup Steps

### 1. Create a GCS Bucket
1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Navigate to Cloud Storage > Buckets
3. Click "Create Bucket"
4. Choose a globally unique name (e.g., `salon-uploads-yourname`)
5. Select a region close to your users
6. Choose "Standard" storage class
7. Set access control to "Fine-grained"
8. Click "Create"

### 2. Make Bucket Public (Optional - for public logo access)
1. Go to your bucket's "Permissions" tab
2. Click "Grant Access"
3. Add principal: `allUsers`
4. Role: "Storage Object Viewer"
5. Save

### 3. Create a Service Account
1. Go to IAM & Admin > Service Accounts
2. Click "Create Service Account"
3. Name: `salon-storage-service`
4. Grant role: "Storage Object Admin"
5. Click "Done"

### 4. Generate Service Account Key
1. Click on your service account
2. Go to "Keys" tab
3. Click "Add Key" > "Create new key"
4. Choose JSON format
5. Save the downloaded JSON file securely

### 5. Configure Environment Variables

Update your `.env` file in the backend directory:

```bash
# Google Cloud Storage Configuration
GCS_BUCKET_NAME=your-bucket-name
GCS_PROJECT_ID=your-gcp-project-id
GOOGLE_APPLICATION_CREDENTIALS=/path/to/your-service-account-key.json
```

For Docker, mount the credentials file in `docker-compose.yml`:

```yaml
backend:
  volumes:
    - ./path/to/service-account-key.json:/app/credentials/gcs-key.json
  environment:
    - GOOGLE_APPLICATION_CREDENTIALS=/app/credentials/gcs-key.json
```

## Local Development (Alternative to GCS)

For local development without GCS, you can:

1. **Use Local File Storage**: Modify `app/core/storage.py` to save files locally instead of GCS
2. **Use GCS Emulator**: Run a local GCS emulator for testing
3. **Mock GCS**: Use environment variable to disable actual uploads during development

## Features Implemented

### Logo Management
- **Upload Custom Logo**: JPG, JPEG, PNG up to 5MB
- **Predefined Icons**: 10 beauty-related Lucide icons
- **Storage**: Logos stored in `logos/` folder in GCS bucket
- **Access**: Public URLs for logos displayed on web client

### Security
- File type validation (only images)
- File size limits (5MB max)
- Authentication required for uploads
- Only salon admin can manage their salon's logo

## API Endpoints

### Upload Logo
```
POST /api/v1/files/upload-logo
Content-Type: multipart/form-data
Authorization: Bearer <token>

Body: file (image file)
```

### Update to Predefined Icon
```
PUT /api/v1/files/logo-icon
Content-Type: application/json
Authorization: Bearer <token>

Body: { "logo_icon_name": "scissors" }
```

### Get Available Icons
```
GET /api/v1/files/beauty-icons
```

### Get File Details
```
GET /api/v1/files/{file_id}
Authorization: Bearer <token>
```

### Delete File
```
DELETE /api/v1/files/{file_id}
Authorization: Bearer <token>
```

## Available Beauty Icons

1. **scissors** - Hair cutting
2. **sparkles** - Beauty/Glamour
3. **heart** - Love/Beauty
4. **flower** - Spa/Nature
5. **star** - Premium/Excellence
6. **zap** - Energy/Quick
7. **crown** - Royal/Premium
8. **feather** - Light/Elegant
9. **smile** - Happy/Satisfaction
10. **palette** - Makeup/Artistry

## Troubleshooting

### "Failed to initialize GCS client"
- Check that `GOOGLE_APPLICATION_CREDENTIALS` path is correct
- Verify the JSON key file is valid
- Ensure the service account has proper permissions

### "Failed to upload file to storage"
- Check bucket name is correct
- Verify service account has "Storage Object Admin" role
- Check network connectivity to GCS

### "File not found" errors
- Ensure bucket exists
- Check file permissions
- Verify bucket is in the correct project

## Cost Considerations

- **Storage**: ~$0.02/GB/month (Standard class)
- **Operations**: Upload/download operations are minimal cost
- **Bandwidth**: First 1GB egress free per month

For a typical salon platform:
- 100 salons × 500KB logo = 50MB storage
- Monthly cost: < $0.01

## Security Best Practices

1. **Never commit** service account keys to version control
2. **Use environment variables** for all GCS configuration
3. **Rotate keys** regularly (every 90 days recommended)
4. **Grant minimum permissions** needed
5. **Monitor bucket access** in GCP Console
6. **Enable Cloud Audit Logs** for production

## Production Deployment

For production on Google Cloud (Cloud Run, App Engine, GKE):
1. Use Workload Identity instead of service account keys
2. Enable Cloud CDN for faster logo delivery
3. Set up Cloud Armor for DDoS protection
4. Configure object lifecycle policies for old files
5. Enable versioning for important files

## Support

For GCS issues, refer to:
- [GCS Documentation](https://cloud.google.com/storage/docs)
- [Python Client Library](https://cloud.google.com/python/docs/reference/storage/latest)
- [Pricing Calculator](https://cloud.google.com/products/calculator)
