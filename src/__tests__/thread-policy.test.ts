import assert from "node:assert/strict";
import test from "node:test";
import { shouldUseEphemeralThread } from "../subprocess/thread-policy.js";

test("web-backed models require persistent native Codex threads", () => {
  assert.equal(shouldUseEphemeralThread("chatgpt-web/gpt-6-sol"), false);
  assert.equal(shouldUseEphemeralThread("chatgpt-web/gpt-6-sol-instant"), false);
  assert.equal(shouldUseEphemeralThread("chatgpt-web/gpt-5.6-sol"), false);
});

test("native Codex models retain ephemeral threads", () => {
  assert.equal(shouldUseEphemeralThread("gpt-6-sol"), true);
  assert.equal(shouldUseEphemeralThread("gpt-6.1-sol"), true);
  assert.equal(shouldUseEphemeralThread("not-chatgpt-web/gpt-6-sol"), true);
});
