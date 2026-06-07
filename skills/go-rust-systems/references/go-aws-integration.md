# AWS & Cloud Integration

## AWS SDK for Go (v2)

**Client Configuration:**

```go
import (
    "context"
    "fmt"

    "github.com/aws/aws-sdk-go-v2/aws"
    "github.com/aws/aws-sdk-go-v2/config"
    "github.com/aws/aws-sdk-go-v2/service/s3"
)

// GOOD: Client factory with retry configuration.
func NewS3Client(ctx context.Context, region string) (*s3.Client, error) {
    cfg, err := config.LoadDefaultConfig(ctx,
        config.WithRegion(region),
        config.WithRetryMaxAttempts(5),
    )
    if err != nil {
        return nil, fmt.Errorf("failed to load AWS config: %w", err)
    }
    return s3.NewFromConfig(cfg), nil
}
```

**Error Handling:**

```go
import (
    "errors"
    "fmt"
    "io"
    "github.com/aws/aws-sdk-go-v2/aws"
    "github.com/aws/aws-sdk-go-v2/service/s3"
    "github.com/aws/aws-sdk-go-v2/service/s3/types"
    "github.com/aws/smithy-go"
)

func GetObject(ctx context.Context, client *s3.Client, bucket, key string) ([]byte, error) {
    const maxObjectReadBytes = 10 << 20 // 10 MiB safety bound

    result, err := client.GetObject(ctx, &s3.GetObjectInput{
        Bucket: aws.String(bucket),
        Key:    aws.String(key),
    })
    if err != nil {
        var nsk *types.NoSuchKey
        if errors.As(err, &nsk) {
            return nil, fmt.Errorf("object not found: %w", ErrNotFound)
        }

        var apiErr smithy.APIError
        if errors.As(err, &apiErr) {
            return nil, fmt.Errorf("AWS API error: %s - %s", apiErr.ErrorCode(), apiErr.ErrorMessage())
        }

        return nil, fmt.Errorf("failed to get object: %w", err)
    }
    defer result.Body.Close()

    body, err := io.ReadAll(io.LimitReader(result.Body, maxObjectReadBytes+1))
    if err != nil {
        return nil, fmt.Errorf("read object body: %w", err)
    }
    if len(body) > maxObjectReadBytes {
        return nil, fmt.Errorf("object body exceeds %d bytes", maxObjectReadBytes)
    }
    return body, nil
}
```

**Pagination:**

```go
import "github.com/aws/aws-sdk-go-v2/service/s3"

func ListObjects(ctx context.Context, client *s3.Client, bucket string) ([]string, error) {
    var keys []string
    paginator := s3.NewListObjectsV2Paginator(client, &s3.ListObjectsV2Input{
        Bucket: aws.String(bucket),
    })

    for paginator.HasMorePages() {
        page, err := paginator.NextPage(ctx)
        if err != nil {
            return nil, fmt.Errorf("failed to list objects: %w", err)
        }

        for _, obj := range page.Contents {
            keys = append(keys, aws.ToString(obj.Key))
        }
    }

    return keys, nil
}
```

**Lambda Handler Pattern:**

```go
import (
    "context"
    "log"

    "github.com/aws/aws-lambda-go/lambda"
    "github.com/aws/aws-sdk-go-v2/aws"
    "github.com/aws/aws-sdk-go-v2/config"
    "github.com/aws/aws-sdk-go-v2/service/dynamodb"
    "github.com/aws/aws-sdk-go-v2/service/dynamodb/types"
)

type Event struct {
    UserID string `json:"user_id"`
}

type Response struct {
    StatusCode int    `json:"status_code"`
    Body       string `json:"body"`
}

func handler(client *dynamodb.Client) func(context.Context, Event) (Response, error) {
    return func(ctx context.Context, event Event) (Response, error) {
        result, err := client.GetItem(ctx, &dynamodb.GetItemInput{
            TableName: aws.String("users"),
            Key: map[string]types.AttributeValue{
                "id": &types.AttributeValueMemberS{Value: event.UserID},
            },
        })
        if err != nil {
            return Response{StatusCode: 500, Body: "Internal error"}, err
        }
        _ = result // Build the real response from result.Item.

        return Response{StatusCode: 200, Body: "Success"}, nil
    }
}

func main() {
    ctx := context.Background()
    cfg, err := config.LoadDefaultConfig(ctx)
    if err != nil {
        log.Fatalf("load AWS config: %v", err)
    }
    lambda.Start(handler(dynamodb.NewFromConfig(cfg)))
}
```

**Context Propagation:**

```go
func ProcessWithTimeout(ctx context.Context, client *s3.Client, bucket, key string) error {
    // Create context with timeout
    ctx, cancel := context.WithTimeout(ctx, 30*time.Second)
    defer cancel()

    // Context automatically propagates cancellation
    _, err := client.GetObject(ctx, &s3.GetObjectInput{
        Bucket: aws.String(bucket),
        Key:    aws.String(key),
    })
    if err != nil {
        if errors.Is(err, context.DeadlineExceeded) {
            return fmt.Errorf("operation timed out: %w", err)
        }
        return fmt.Errorf("failed to get object: %w", err)
    }

    return nil
}
```

**Region Validation:**

```go
var allowedRegions = map[string]bool{
    "us-east-1": true,
    "us-west-2": true,
    "eu-west-1": true,
}

func ValidateRegion(region string) error {
    if !allowedRegions[region] {
        return fmt.Errorf("invalid region: %s", region)
    }
    return nil
}
```
