import ChatMessage from './ChatMessage';

export default {
  title: 'Components/Chat/ChatMessage',
  component: ChatMessage,
  tags: ['autodocs'],
  parameters: {
    layout: 'centered',
  },
};

export const UserMessage = {
  args: {
    message: {
      role: 'user',
      content: 'What is our password policy?',
    },
  },
};

export const AssistantMessage = {
  args: {
    message: {
      role: 'assistant',
      content: 'Based on the company policy, passwords must be at least 12 characters long and must be changed every 90 days.',
      sources: [
        {
          document_name: 'Password Policy',
          page_number: 1,
        },
        {
          document_name: 'Password Policy',
          page_number: 2,
        },
      ],
    },
  },
};

export const AssistantMessageWithLongText = {
  args: {
    message: {
      role: 'assistant',
      content: 'According to our company policy, passwords must meet the following requirements:\n\n1. Be at least 12 characters long\n2. Include at least one uppercase letter\n3. Include at least one lowercase letter\n4. Include at least one number\n5. Include at least one special character\n6. Must not contain your username or parts of your full name\n7. Must be changed every 90 days\n8. Cannot reuse any of your previous 10 passwords',
      sources: [
        {
          document_name: 'Password Policy',
          page_number: 1,
        },
        {
          document_name: 'Security Guidelines',
          page_number: 15,
        },
      ],
    },
  },
};