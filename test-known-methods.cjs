const { createClient } = require('@supabase/supabase-js');

const SUPABASE_URL = 'https://kolgqfjgncdwddziqloz.supabase.co';
const SUPABASE_SERVICE_KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImtvbGdxZmpnbmNkd2RkemlxbG96Iiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc1NjczODc2MSwiZXhwIjoyMDcyMzE0NzYxfQ.xPoR2Q_yey7AQcorPG3iBLKTadzzSEMmK3eM9ZW46Qc';

const supabase = createClient(SUPABASE_URL, SUPABASE_SERVICE_KEY);

async function testKnownMethods() {
  const methodsToTest = ['api', 'email', 'web_form', 'form', 'manual'];

  console.log('Testing known submission_method values:');
  for (const method of methodsToTest) {
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
      console.log(`  ✗ "${method}": REJECTED`);
    } else {
      console.log(`  ✓ "${method}": ACCEPTED`);
      // Clean up
      await supabase.from('directories').delete().eq('id', testRecord.id);
    }
  }
}

testKnownMethods();
