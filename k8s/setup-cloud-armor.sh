#!/bin/bash

# Create Cloud Armor Security Policy
echo "Creating Cloud Armor security policy..."

gcloud compute security-policies create cloud-armor-policy \
    --description "Security policy for FastAPI Todo App"

# Add rate limiting rule
gcloud compute security-policies rules create 3000 \
    --security-policy cloud-armor-policy \
    --action "rate_based_ban" \
    --rate-limit-threshold-count 100 \
    --rate-limit-threshold-interval-sec 60 \
    --conform-action "allow" \
    --exceed-action "deny-429" \
    --enforce-on-key "IP" \
    --description "Rate limit: 100 requests per minute per IP"

# Add default allow rule (optional, as there's usually a default)
gcloud compute security-policies rules create 1000 \
    --security-policy cloud-armor-policy \
    --action "allow" \
    --src-ip-ranges "*" \
    --description "Allow all traffic by default"

echo "Cloud Armor policy created successfully!"
echo "You can view it at: https://console.cloud.google.com/net-security/securitypolicies/list"
