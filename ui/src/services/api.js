export async function getMemories(baseUrl = "/api") {
  const response = await fetch(`${baseUrl}/memories`);
  if (!response.ok) throw new Error(`Memory request failed: ${response.status}`);
  return response.json();
}
