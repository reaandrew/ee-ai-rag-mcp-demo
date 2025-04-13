import React from 'react';
import { Routes, Route } from 'react-router-dom';
import Header from './components/layout/Header';
import Footer from './components/layout/Footer';
import ChatPage from './pages/ChatPage';

function App() {
  return (
    <div className="govuk-template__body">
      <Header />
      <div className="govuk-width-container">
        <main className="govuk-main-wrapper" id="main-content" role="main">
          <Routes>
            <Route path="/" element={<ChatPage />} />
          </Routes>
        </main>
      </div>
      <Footer />
    </div>
  );
}

export default App;