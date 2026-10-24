/** Browser-backed models need a persisted native Codex thread to retain trusted task context. */
export function shouldUseEphemeralThread(model: string): boolean {
  return !model.startsWith("chatgpt-web/");
}
