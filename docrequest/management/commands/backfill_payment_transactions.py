from django.core.management.base import BaseCommand
from django.utils import timezone
from docrequest.models import DocumentRequest, PaymentTransaction

class Command(BaseCommand):
    help = 'Create PaymentTransaction records for existing paid requests'

    def handle(self, *args, **kwargs):
        created_count = 0
        skipped_count = 0
        
        self.stdout.write(self.style.WARNING('='*60))
        self.stdout.write(self.style.WARNING('Backfilling Payment Transactions...'))
        self.stdout.write(self.style.WARNING('='*60 + '\n'))
        
        # Get all paid requests
        paid_requests = DocumentRequest.objects.filter(payment_status='paid')
        
        self.stdout.write(f'Found {paid_requests.count()} paid request(s)\n')
        
        for req in paid_requests:
            # Check if payment transaction already exists
            existing_txn = PaymentTransaction.objects.filter(
                request=req,
                transaction_type='payment'
            ).first()
            
            if existing_txn:
                skipped_count += 1
                self.stdout.write(f'  ⊗ Skipped {req.order_id} - transaction already exists')
                continue
            
            # Create payment transaction
            PaymentTransaction.objects.create(
                request=req,
                transaction_type='payment',
                amount=req.payment_amount,
                status='completed',
                payment_method=req.payment_method,
                processed_at=req.payment_date or req.created_at,
                notes=f"Backfilled payment transaction for {req.order_id}"
            )
            
            created_count += 1
            self.stdout.write(
                self.style.SUCCESS(f'  ✅ Created payment transaction for {req.order_id} - ₱{req.payment_amount}')
            )
        
        self.stdout.write('\n' + '='*60)
        self.stdout.write(self.style.SUCCESS('SUMMARY:'))
        self.stdout.write('='*60)
        self.stdout.write(f'  • Transactions created: {created_count}')
        self.stdout.write(f'  • Already existed:      {skipped_count}')
        self.stdout.write(f'  • Total processed:      {paid_requests.count()}')
        self.stdout.write('='*60 + '\n')
        
        if created_count > 0:
            self.stdout.write(
                self.style.SUCCESS(f'✅ Successfully created {created_count} payment transaction(s)!\n')
            )
        else:
            self.stdout.write(
                self.style.SUCCESS('✅ All paid requests already have payment transactions!\n')
            )