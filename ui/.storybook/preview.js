import { BrowserRouter } from 'react-router-dom';
import { AuthProvider } from '../src/contexts/AuthContext';
import '../src/styles/main.scss';

/** @type { import('@storybook/react').Preview } */
const preview = {
  parameters: {
    actions: { argTypesRegex: "^on[A-Z].*" },
    controls: {
      matchers: {
        color: /(background|color)$/i,
        date: /Date$/,
      },
    },
  },
  decorators: [
    (Story) => (
      <BrowserRouter>
        <AuthProvider>
          <div className="govuk-width-container">
            <main className="govuk-main-wrapper">
              <Story />
            </main>
          </div>
        </AuthProvider>
      </BrowserRouter>
    ),
  ],
};

export default preview;