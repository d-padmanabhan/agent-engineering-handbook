# Protobuf Schema Evolution

The schema is the contract. Once the contract is published (used by even one other service), the rules become non-negotiable. Break them and you corrupt every other instance of the message in flight, at rest, or in any consumer's local cache.

## The single rule that matters most

**Field numbers are wire identity. Never re-number a field. Ever.**

The wire format encodes `(field_number, wire_type, value)`. The field *name* is not on the wire. If you re-number `id` from 1 to 2, every existing serialized payload now has `id` in the slot of whatever was previously field 2 - the data is silently corrupted, not rejected.

## The full rules

| Change | Compatible? | Notes |
|---|---|---|
| Add a new field with a new (unused) number | **Yes** (forward + backward) | Old code ignores; new code reads |
| Remove a field, **reserve the number** | **Yes** | `reserved 4;` prevents future reuse |
| Re-number a field | **NO** | Wire-incompatible; corrupts data |
| Change field type (int32 <-> int64) | **Sometimes** | Same wire type kind (varint) - safe in proto3. string <-> bytes - safe. Anything else - no. |
| Rename a field (number unchanged) | **Yes** | Wire is by number, not name |
| Change `repeated` to single | **NO** | Wire format differs |
| Change single to `repeated` | **Yes** in proto3 (single becomes a one-element list) | Caveat: scalar zero-value handling |
| Add value to an enum | **Yes** (backward-compatible) | Old code sees `UNRECOGNIZED` |
| Remove a value from an enum | **Risky** | Existing data may carry the value |
| Move a field into / out of a `oneof` | **NO** | Wire format differs |
| Add a `oneof` | **Yes** | New oneof, new fields |
| Make a required field optional (proto2) | **Yes** | (proto3 has no required) |
| Change package or message name | **NO** | Fully-qualified name is part of identity (for `Any`, reflection) |

## The reserved keyword

When you remove a field, *reserve its number and its name*:

```protobuf
message User {
  string id = 1;
  string email = 2;
  // string display_name = 3;     // removed
  reserved 3;
  reserved "display_name";
}
```

Now nobody can accidentally add `string nickname = 3;` and corrupt existing data.

## Proto3 presence semantics

The infamous trap. In proto3, scalar fields with their default value (zero / empty string / false) **do not appear on the wire**. The receiver cannot distinguish "field set to 0" from "field absent".

```protobuf
message UpdateUserRequest {
  int32 max_attempts = 1;   // sender sets to 0 - receiver sees nothing
}
```

If `0` is a meaningful "set to zero, don't retry" signal, the receiver will never know. They'll fall back to their default (which might be 5).

### Three fixes

**1. `optional` keyword (proto3 since release 3.15, 2020):**

```protobuf
message UpdateUserRequest {
  optional int32 max_attempts = 1;   // presence tracked separately
}
```

In code, you can check `req.has_max_attempts()` distinct from `req.max_attempts == 0`.

**2. Wrapper types** (`google/protobuf/wrappers.proto`):

```protobuf
import "google/protobuf/wrappers.proto";

message UpdateUserRequest {
  google.protobuf.Int32Value max_attempts = 1;
}
```

`max_attempts` is now a message (which can be null/absent), not a scalar.

**3. Sentinel values** (last resort, hard to maintain):

Reserve a sentinel like `-1` that means "absent". Brittle; document loudly.

Prefer **`optional`** for new code; **wrapper types** if you're stuck on a pre-2020 toolchain.

## Wire-format gotchas

### Field numbers 1-15 are 1-byte tags; 16+ are 2-byte

Reserve `1-15` for high-frequency fields. Once your message has more than 15 fields, you've committed to 2-byte tags on every field beyond. Plan numbering upfront.

```protobuf
message TelemetrySample {
  // Hot fields (every message) - 1-byte tags
  int64 timestamp_ns = 1;
  string sensor_id = 2;
  double value = 3;
  // ... up to 15

  // Cold fields (sparse) - 2-byte tags ok
  string debug_label = 16;
  repeated string tags = 17;
}
```

### Unknown fields preservation

Most modern Protobuf libraries (Go, Java, Python after 3.5) **preserve unknown fields** by default during round-trips. This is what allows newer consumers to add fields that older consumers don't break on.

Don't disable this. Don't strip unknown fields in middleware. You'll silently destroy data that newer clients depend on.

### `bytes` vs `string`

| Type | Wire | Validation |
|---|---|---|
| `string` | UTF-8 bytes prefixed by length | UTF-8 validated (most libs) |
| `bytes` | Raw bytes prefixed by length | No validation |

Use `bytes` for binary payloads, hashes, raw protobuf-as-bytes, anything non-textual. Use `string` for human-readable text. Mixing them up causes hard-to-debug encoding errors when binary data flows through code paths that try to decode as UTF-8.

### `Any` (well-known type) for opaque messages

```protobuf
import "google/protobuf/any.proto";

message Event {
  string type = 1;
  google.protobuf.Any payload = 2;
}
```

Lets you carry an opaque sub-message without depending on its `.proto` at compile time. Useful for event envelopes. Cost: receiver must know the type URL to unpack; if the receiver doesn't have the schema, the message is opaque.

### `oneof` semantics

```protobuf
message UpdateRequest {
  string id = 1;
  oneof update {
    string new_name = 2;
    int32 new_age = 3;
    bool delete = 4;
  }
}
```

- Only one of `new_name`, `new_age`, `delete` is set at a time.
- Setting one clears the others (in code-gen for most languages).
- A `oneof` cannot contain `repeated` fields directly (workaround: wrap in a sub-message).
- Adding a new field to an existing `oneof` is **NOT** compatible - old code doesn't know about the new case.

## Versioning packages

```protobuf
package myorg.users.v1;
// ...

// One day later, breaking changes accumulate
package myorg.users.v2;
```

Treat the package as the unit of versioning, not individual messages. v1 stays around for backward compatibility; v2 is a new contract.

Some teams version on the **service** rather than the package:

```protobuf
service UsersV1 { ... }
service UsersV2 { ... }
```

Either works. Pick one convention and stick to it.

## Tooling

| Tool | What |
|---|---|
| [buf](https://buf.build/) | Linter, breaking-change detector, code-gen. `buf breaking` against a baseline catches every rule violation above |
| [protoc](https://github.com/protocolbuffers/protobuf) | Reference compiler; needed for language-specific code-gen unless you use `buf` |
| [grpcurl](https://github.com/fullstorydev/grpcurl) | Curl for gRPC; needs reflection server or the `.proto` file |
| [protovalidate](https://github.com/bufbuild/protovalidate) | Cross-language validation rules expressed in the `.proto` |

**Add `buf breaking` to CI** on every PR that touches a `.proto`. It will catch field renumbers, removed-without-reserved, type changes, and oneof changes. It is the single highest-value gate for protobuf schema discipline.

```yaml
# .buf.yaml
version: v1
breaking:
  use:
    - WIRE_JSON
```

```yaml
# CI step
- name: Check protobuf breaking changes
  run: buf breaking --against '.git#branch=main'
```

## Anti-patterns

1. **Re-numbering a field.** The single most catastrophic protobuf mistake.
2. **Removing a field without reserving the number.** Sets up the next developer to corrupt data.
3. **Scalar field for true "optional" semantics in proto3.** Use `optional` or wrapper types.
4. **Renaming the package** without versioning. Breaks `Any`, reflection, and tooling that loads schemas by FQN.
5. **Stripping unknown fields in middleware.** Destroys forward compatibility.
6. **`message Foo { int32 type = 1; ... }` instead of `enum`.** Lose enumerability, validation, and tooling.
7. **`required` (proto2 only).** proto3 has no required; if you're on proto2, avoid required - the field can never be removed.
8. **No `buf breaking` in CI.** Schema discipline is a CI gate, not a code-review hope.
9. **Generated code in source control AND in CI.** Pick one. Mixed states drift.
10. **One giant `.proto` file with everything.** Split by service / domain; circular imports are a real problem.
