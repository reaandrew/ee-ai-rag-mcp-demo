import React from 'react';
import { Link } from 'react-router-dom';

const Header = () => {
  return (
    <header className="govuk-header" role="banner" data-module="govuk-header">
      <div className="govuk-header__container govuk-width-container">
        <div className="govuk-header__logo">
          <Link to="/" className="govuk-header__link govuk-header__link--homepage">
            <span className="govuk-header__logotype">
              <span className="govuk-header__logotype-text">
                Policy Search
              </span>
            </span>
          </Link>
        </div>
        <div className="govuk-header__content">
          <nav aria-label="Menu" className="govuk-header__navigation">
            <ul className="govuk-header__navigation-list">
              <li className="govuk-header__navigation-item">
                <span className="govuk-header__navigation-item">
                  RAG Policy Assistant
                </span>
              </li>
            </ul>
          </nav>
        </div>
      </div>
    </header>
  );
};

export default Header;