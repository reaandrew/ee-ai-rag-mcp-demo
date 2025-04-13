import React from 'react';

const SourceCitation = ({ source }) => {
  const { document_name, page_number } = source;
  
  return (
    <div className="source-citation">
      <span className="source-citation__document">{document_name}</span>
      {page_number && (
        <span className="source-citation__page">, Page {page_number}</span>
      )}
    </div>
  );
};

export default SourceCitation;