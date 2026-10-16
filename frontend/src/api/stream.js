// Fetch SSE may split UTF-8 characters or events at any byte boundary.
export async function readChatStream(response, onEvent) {
  if (!response.body) throw new Error("Streaming is unavailable in this browser.");
  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "", completed = false;
  function consume(frame) {
    const data = frame.split("\n").filter(l => l.startsWith("data:")).map(l => l.slice(5).trimStart()).join("\n");
    if (!data) return;
    const event = JSON.parse(data);
    if (event.error) throw new Error(event.error);
    if (event.done) completed = true;
    onEvent(event);
  }
  try {
    while (true) {
      const { value, done } = await reader.read();
      buffer += done ? decoder.decode() : decoder.decode(value, { stream: true });
      buffer = buffer.replace(/\r\n/g, "\n");
      let boundary;
      while ((boundary = buffer.indexOf("\n\n")) !== -1) {
        consume(buffer.slice(0, boundary)); buffer = buffer.slice(boundary + 2);
      }
      if (done) break;
    }
    if (buffer.trim()) consume(buffer);
    if (!completed) throw new Error("The connection ended before the answer was saved. Please retry.");
  } finally { await reader.cancel().catch(() => {}); reader.releaseLock(); }
}
