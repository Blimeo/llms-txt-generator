export default function HomePage() {
  return (
    <main className="p-8">
      <h1 className="text-2xl font-bold">LLMs.txt Generator</h1>
      <form className="mt-4 space-y-2">
        <input
          type="url"
          name="url"
          placeholder="https://example.com"
          className="border rounded p-2 w-full"
        />
        <button type="submit" className="bg-blue-600 text-white px-4 py-2 rounded">
          Generate
        </button>
      </form>
    </main>
  );
}