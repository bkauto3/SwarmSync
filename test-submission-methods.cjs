const fs = require('fs');
const { createClient } = require('@supabase/supabase-js');

const SUPABASE_URL = 'https://kolgqfjgncdwddziqloz.supabase.co';
const SUPABASE_SERVICE_KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImtvbGdxZmpnbmNkd2RkemlxbG96Iiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc1NjczODc2MSwiZXhwIjoyMDcyMzE0NzYxfQ.xPoR2Q_yey7AQcorPG3iBLKTadzzSEMmK3eM9ZW46Qc';

const supabase = createClient(SUPABASE_URL, SUPABASE_SERVICE_KEY);

async function testSubmissionMethods() {
  // Read CSV and extract unique submission_method values
  const csvContent = fs.readFileSync(
    'C:\\Users\\Ben\\Desktop\\Github\\Agent-Market\\456 TOTAL DIRECTORIES For Genesis.csv',
    'utf-8'
  );

  const lines = csvContent.split('\n');
  const headerLine = lines[0];
  const headers = headerLine.split(',');
  const submissionMethodIndex = headers.findIndex(h => h.includes('submission_method'));

  console.log('submission_method column index:', submissionMethodIndex);

  const uniqueMethods = new Set();
  for (let i = 1; i < lines.length; i++) {
    if (!lines[i].trim()) continue;
    const parts = lines[i].split(',');
    if (parts[submissionMethodIndex]) {
      uniqueMethods.add(parts[submissionMethodIndex].trim());
    }
  }

  console.log('\nUnique submission_method values in CSV:');
  uniqueMethods.forEach(method => console.log(`  - ${method}`));

  // Test each value
  console.log('\nTesting each value against database constraint:');
  for (const method of uniqueMethods) {
    const testRecord = {
      id: '00000000-0000-0000-0000-000000000001',
      name: 'Test Directory',
      website: 'https://test.com',
      category: 'test',
      submission_method: method,
      active: true
    };

    const { error } = await supabase
      .from('directories')
      .insert(testRecord);

    if (error) {
      console.log(`  ✗ ${method}: REJECTED - ${error.message}`);
    } else {
      console.log(`  ✓ ${method}: ACCEPTED`);
      // Clean up
      await supabase.from('directories').delete().eq('id', testRecord.id);
    }
  }
}

testSubmissionMethods();
