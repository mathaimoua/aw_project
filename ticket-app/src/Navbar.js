import './Navbar.css';

export default function Navbar() {
  return (
    <nav className="navbar">
      <div className="navbar-inner">
        <span className="navbar-title">
          <span className="navbar-title-atm">ATM</span>
          <span className="navbar-title-divider">–</span>
          <span className="navbar-title-full">Andersen Ticket Monster</span>
        </span>
      </div>
    </nav>
  );
}
