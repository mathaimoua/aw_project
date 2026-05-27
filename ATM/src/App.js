import './App.css';
import Navbar from './Navbar';
import TicketForm from './TicketForm';

function App() {
  return (
    <>
      <Navbar />
      <main className="app-shell">
        <TicketForm />
      </main>
    </>
  );
}

export default App;
