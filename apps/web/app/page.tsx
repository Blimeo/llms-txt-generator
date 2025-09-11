import { createClient } from '../utils/supabase/client'
import { cookies } from 'next/headers'

export default async function HomePage() {
  const cookieStore = await cookies()
  const supabase = createClient(cookieStore)

  const { data: todos } = await supabase.from('todos').select()

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
      {todos && (
        <ul className="mt-6 space-y-2">
          {todos.map((todo) => (
            <li key={todo.id} className="border-b pb-2">
              {todo.name}
            </li>
          ))}
        </ul>
      )}
    </main>
  );
}