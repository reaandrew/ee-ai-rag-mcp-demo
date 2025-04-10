# Auth Authorizer Lambda Function

This Lambda function serves as a custom authorizer for the API Gateway. In its current implementation, it's a placeholder that always authorizes requests, but logs important information for audit purposes.

## Flow

1. API Gateway receives a request and invokes this authorizer
2. The authorizer logs details about the request (source IP, user agent, etc.)
3. The authorizer returns an IAM policy document allowing the request
4. API Gateway proceeds with the request if authorized

## Authorizer Response Format

```json
{
  "principalId": "user",
  "policyDocument": {
    "Version": "2012-10-17",
    "Statement": [
      {
        "Action": "execute-api:Invoke",
        "Effect": "Allow",
        "Resource": "arn:aws:execute-api:region:account-id:api-id/stage/method/resource"
      }
    ]
  },
  "context": {
    "stringKey": "value",
    "numberKey": 123,
    "booleanKey": true
  }
}
```

## Future Enhancements

This placeholder authorizer can be enhanced to:

1. Validate API keys or authentication tokens
2. Implement role-based access control
3. Rate limiting and throttling
4. Integration with identity providers