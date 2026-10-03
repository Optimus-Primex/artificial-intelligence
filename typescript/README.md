# @optimus-primex/ai-client

Typed TypeScript client for the Stellar AI service.

## Install

```bash
npm install @optimus-primex/ai-client
```

## Usage

```ts
import { AiClient } from "@optimus-primex/ai-client";

const client = new AiClient("http://127.0.0.1:8000");

await client.health();
await client.networkStatus("testnet");
await client.analyze({ network: "testnet" });
await client.chat({ message: "Is the network healthy?", network: "testnet" });
```

## Develop

```bash
npm install
npm run lint    # typecheck
npm run build   # emit dist/
npm test        # vitest
```
