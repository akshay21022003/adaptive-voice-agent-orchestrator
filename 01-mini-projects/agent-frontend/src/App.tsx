import { useState } from 'react'

function App() {
  const [count, setCount] = useState(0)

  return (
    <button
      type="button"
      onClick={() => setCount((c) => c + 1)}
      className="mt-6 rounded-lg bg-purple-600 px-5 py-2 font-medium text-white transition hover:bg-purple-700 active:scale-95"
    >
      Count is {count}
    </button>
  )
}

export default App
