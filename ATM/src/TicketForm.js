import { useState } from 'react';
import { supabase } from './supabaseClient';
import './TicketForm.css';

const PRIORITIES = ['Low', 'Medium', 'High'];

const initialState = {
  user: 'Matthew Moua',
  title: '',
  description: '',
  priority: 'Medium',
  keywords: '',
};

export default function TicketForm() {
  const [form, setForm] = useState(initialState);
  const [submitted, setSubmitted] = useState(false);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);

  function handleChange(e) {
    const { name, value } = e.target;
    setForm((prev) => ({ ...prev, [name]: value }));
  }

  async function handleSubmit(e) {
    e.preventDefault();
    setLoading(true);
    setError(null);

    const { error: insertError } = await supabase.from('ticket_requests').insert({
      submitted_by: form.user,
      title: form.title,
      description: form.description,
      priority: form.priority,
      keywords: form.keywords
        .split(',')
        .map((k) => k.trim())
        .filter(Boolean),
    });

    setLoading(false);

    if (insertError) {
      setError(insertError.message);
      return;
    }

    setSubmitted(true);
  }

  function handleReset() {
    setForm(initialState);
    setSubmitted(false);
  }

  if (submitted) {
    return (
      <div className="ticket-card">
        <h2 className="success-title">Ticket submitted</h2>
        <p className="success-message">
          Your ticket <strong>"{form.title}"</strong> has been received.
        </p>
        <button className="btn btn-secondary" onClick={handleReset}>
          Submit another
        </button>
      </div>
    );
  }

  return (
    <div className="ticket-card">
      <h2 className="form-title">Submit a Ticket</h2>
      <form onSubmit={handleSubmit} noValidate>
        <div className="field">
          <label htmlFor="title">Title</label>
          <input
            id="title"
            name="title"
            type="text"
            placeholder="Brief summary of the issue"
            value={form.title}
            onChange={handleChange}
            required
          />
        </div>

        <div className="field">
          <label htmlFor="description">Description</label>
          <textarea
            id="description"
            name="description"
            rows={5}
            placeholder="Describe the issue in detail..."
            value={form.description}
            onChange={handleChange}
            required
          />
        </div>

        <div className="field">
          <label htmlFor="keywords">Keywords</label>
          <input
            id="keywords"
            name="keywords"
            type="text"
            placeholder="e.g. account access, error message, display issue"
            value={form.keywords}
            onChange={handleChange}
          />
          <span className="field-hint">Separate keywords with commas</span>
        </div>

        <div className="field">
          <label htmlFor="priority">Priority</label>
          <select
            id="priority"
            name="priority"
            value={form.priority}
            onChange={handleChange}
          >
            {PRIORITIES.map((p) => (
              <option key={p} value={p}>
                {p}
              </option>
            ))}
          </select>
        </div>

        {error && <p className="form-error">{error}</p>}

        <button className="btn btn-primary" type="submit" disabled={loading}>
          {loading ? 'Submitting…' : 'Submit ticket'}
        </button>
      </form>
    </div>
  );
}
