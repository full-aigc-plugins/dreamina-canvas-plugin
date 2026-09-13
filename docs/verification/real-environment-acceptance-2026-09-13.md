# Dreamina Canvas real-environment acceptance

Date: 2026-09-13

Environment: `profile=default`, `region=cn`, `environment=prod`

CLI: `1.0.0`, commit `ae2c968`, edition `public`, distribution `cn`

Plugin source under acceptance: `main@945975c97e89014cc14a2997b0487b0dafec8a13`.
The runtime findings were then incorporated into upstream Skills at
`397eb1f2b7d91930e3cddd93735706b4941fc447`, then extended with complete
official-command ownership at `e8ae5880fb36f71c4e60ef854060ab9cadd9edc4` and
plugin version `0.1.2`.

## Scope and authorization

The acceptance used a dedicated server-side canvas:

```text
projectId: 7c2773b1-f509-47f2-9443-0942c9cefe7a
name: Codex Canvas 最终真实验收 2026-09-13
```

The user separately approved two bounded paid batches:

- batch 1 ceiling: 56 credits
- batch 2 ceiling: 98 credits, including a 1-credit image upscale
- total approved ceiling: 154 credits
- total observed on completed resources: 152 credits

Credit-confirmation tokens remained in process memory and were never logged or
persisted. Each node had its own persisted lowercase UUID `submitId`; recovery
and bounded retries reused the same IDs.

## Real service matrix

| Capability | Evidence | Result |
|---|---|---|
| version / schema | Live CLI responses | PASS |
| auth status / account | Local state plus server-authenticated account query | PASS |
| image/video/audio model discovery | 7 image, 8 video, 2 audio models | PASS |
| voice discovery | 142 total voices, paginated | PASS |
| canvas create / list / current context | Dedicated project created and listed | PASS |
| text create / edit | Draft saved and sparse edit observed | PASS |
| image t2i / i2i | Both generated to terminal success | PASS |
| video t2v / m2v / first_last_frame | All three generated to terminal success | PASS |
| audio tts / music | Both generated to terminal success | PASS |
| image upscale pro 2K | New 2160×2160 resource generated | PASS |
| Element create / edit | main, voice, and auxiliary follow-node bindings | PASS |
| Timeline create / edit | Visual/audio tracks created, then fully replaced | PASS |
| node find / show | Server-side summaries and full views returned | PASS |
| quote / confirm / run | Bounded quotes, explicit approval, accepted submissions | PASS |
| operation status / wait | Stable IDs reached `succeeded` | PASS |
| resource get / download | Eight resources fetched and atomically downloaded | PASS |

## Runtime drift and defect findings

Real execution found three contract differences that static tests did not
prove:

1. CLI 1.0.0 declares `model list`, while the supplied guide describes
   `model search`.
2. CLI 1.0.0 `voice list` accepts `--offset` and `--count`, but not
   `--language`.
3. Batch `node run` requires one `--submit-id` per `--node-id`, with equal
   length and order. A single batch-wide ID is rejected with exit 2.

The upstream Skills now select discovery commands and optional flags from the
live schema and document the ordered per-node submit-ID mapping. One transient
service exit 21 was recovered by bounded retry with the same IDs. One transient
download exit 21 was safely retried; atomic download semantics left no partial
artifact.

## Verified artifacts

All paths are under the user-approved directory
`out/real-acceptance-2026-09-13/`.

| Mode | Bytes | SHA-256 | Local media probe |
|---|---:|---|---|
| t2i | 582392 | `2172708c488cb2a26861fce36db5604c355a1f1aae4a66e8b48bd4cf2fceebd6` | PNG 1024×1024 |
| t2v | 2029150 | `4f18116dcd5e6b9a27088369ebdb37c124bfaf07ba61ac7d02cd9c98aeb4980e` | H.264/AAC MP4, 640×640, 4.06s |
| tts | 67754 | `a3fca0125311c5017499455b814392d88c16edae9f2a79bb05b0dd4c650b6f2c` | MP3, 44.1kHz stereo, 2.12s |
| music | 961351 | `17cbbff468fbf57c35cad48d6473a54ebaecaad7a596fc2f964f01a18dee3ea2` | MP3, 44.1kHz stereo, 30.04s |
| i2i | 506678 | `004734dadb377edca89af97d909636ab6efab36f0f186541418806f8b8ab7c54` | PNG 1024×1024 |
| m2v | 2119057 | `1cf3a4a2f56b67afe88621e389a8bb64b2f020f1f9dd35332888309dc770bd33` | H.264/AAC MP4, 640×640, 4.06s |
| first_last_frame | 1964855 | `d59846a77ed8297115f0c585b5e31b6fb3f22a5b580cb2e265000f5d6e47c79d` | H.264/AAC MP4, 640×640, 4.06s |
| upscale | 594796 | `bdb445db9daeb72c387cac08f402700c428e4a0229d487fff22baf1d0c1b8177` | PNG 2160×2160 |

For every artifact, the CLI download exit code was 0 and its reported byte
count and SHA-256 matched the final on-disk file. `file` and `ffprobe` confirmed
container, codec, dimensions, duration, sample rate, and channels as applicable.
