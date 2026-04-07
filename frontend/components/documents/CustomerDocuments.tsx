'use client';

import { useState, useEffect } from 'react';
import { Plus } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { DocumentUploadForm } from './DocumentUploadForm';
import { DocumentList } from './DocumentList';
import { documentsAPI } from '@/lib/api/documents';
import { CustomerDocument } from '@/types';

interface CustomerDocumentsProps {
  customerId: string;
  canManage?: boolean;
}

export function CustomerDocuments({ customerId, canManage = false }: CustomerDocumentsProps) {
  const [documents, setDocuments] = useState<CustomerDocument[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [showUploadForm, setShowUploadForm] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchDocuments = async () => {
    setIsLoading(true);
    setError(null);

    try {
      const docs = await documentsAPI.getCustomerDocuments(customerId);
      setDocuments(docs);
    } catch (err: any) {
      console.error('Error fetching documents:', err);
      setError('Failed to load documents');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchDocuments();
  }, [customerId]);

  const handleUploadSuccess = () => {
    setShowUploadForm(false);
    fetchDocuments();
  };

  if (isLoading) {
    return (
      <Card className="p-8">
        <div className="text-center text-muted-foreground">
          <p>Loading documents...</p>
        </div>
      </Card>
    );
  }

  if (error) {
    return (
      <Card className="p-8">
        <div className="text-center text-red-500">
          <p>{error}</p>
          <Button
            variant="outline"
            onClick={fetchDocuments}
            className="mt-4"
          >
            Retry
          </Button>
        </div>
      </Card>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <div>
          <h3 className="text-lg font-semibold">Documents</h3>
          <p className="text-sm text-muted-foreground">
            {documents.length} document{documents.length !== 1 ? 's' : ''} uploaded
          </p>
        </div>
        <Button onClick={() => setShowUploadForm(!showUploadForm)}>
          <Plus className="h-4 w-4 mr-2" />
          {showUploadForm ? 'Hide Form' : 'Upload Document'}
        </Button>
      </div>

      {showUploadForm && (
        <DocumentUploadForm
          customerId={customerId}
          onSuccess={handleUploadSuccess}
          onCancel={() => setShowUploadForm(false)}
        />
      )}

      <DocumentList
        documents={documents}
        onUpdate={fetchDocuments}
        canManage={canManage}
      />
    </div>
  );
}
