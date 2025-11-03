PRAGMA foreign_keys = OFF;
BEGIN TRANSACTION;

-- COUPON
INSERT INTO COUPON (Coupon_ID, Code, Discount_Percentage, Valid_Until, Restaurant_ID) VALUES
 (1, 'SAVE10', 10.00, '2025-12-31', 1),
 (2, 'FREEMEAL', 15.00, '2025-11-15', 2),
 (3, 'HALFOFF', 50.00, '2025-10-01', 1),
 (4, 'FLAT30', 30.00, '2025-08-20', 3),
 (5, 'NEWUSER', 20.00, '2025-09-10', 4),
 (6, 'REPEAT15', 15.00, '2025-07-30', 2),
 (7, 'BIGDEAL', 25.00, '2025-06-05', 3);

-- FOOD_ITEM
INSERT INTO FOOD_ITEM (Food_ID, Name, Description, Price, Category, Availability, Restaurant_ID) VALUES
 (1, 'Burger',    'Cheese burger',      120.00, 'Fast Food', 'Y', 1),
 (2, 'Pizza',     'Margherita',         250.00, 'Italian',   'Y', 1),
 (3, 'Pasta',     'White sauce pasta',  220.00, 'Italian',   'Y', 2),
 (4, 'Fries',     'French fries',       100.00, 'Snacks',    'Y', 1),
 (5, 'Taco',      'Chicken taco',       130.00, 'Mexican',   'Y', 2),
 (6, 'Salad',     'Caesar Salad',       180.00, 'Healthy',   'Y', 2),
 (7, 'Biryani',   'Chicken biryani',     200.00, 'Indian',    'Y', 3),
 (8, 'Sushi',     'Salmon sushi',       300.00, 'Japanese',  'Y', 4),
 (9, 'Sandwich',  'Club sandwich',      150.00, 'Fast Food', 'Y', 3),
 (10,'Paneer Tikka','Spicy tikka',      170.00, 'Indian',    'Y', 4),
 (11,'Noodles',   'Hakka noodles',      160.00, 'Chinese',   'Y', 2),
 (12,'Momos',     'Steamed momos',      120.00, 'Chinese',   'Y', 2),
 (13,'Wrap',      'Veg wrap',           110.00, 'Snacks',    'Y', 1),
 (14,'Brownie',   'Chocolate brownie',   90.00, 'Dessert',   'Y', 3),
 (15,'Ice Cream', 'Vanilla scoop',       80.00, 'Dessert',   'Y', 4),
 (16,'Donut',     'Sugar donut',         70.00, 'Dessert',   'Y', 3),
 (17,'Coffee',    'Cappuccino',         140.00, 'Beverage',  'Y', 4),
 (18,'Tea',       'Masala tea',          50.00, 'Beverage',  'Y', 3),
 (19,'Juice',     'Orange juice',        90.00, 'Beverage',  'Y', 2),
 (20,'Thali',     'Veg thali',          180.00, 'Indian',    'Y', 1);

-- CUSTOMER
INSERT INTO CUSTOMER (Customer_ID, Name, Email, Password, Phone_Number, Address, User_Type) VALUES
 (1,  'Aman Gupta',   'aman@gmail.com',   'pass1',  '9876543210', 'Delhi',       'Regular'),
 (2,  'Neha Verma',   'neha@gmail.com',   'pass2',  '9876543211', 'Mumbai',      'Regular'),
 (3,  'Ravi Kumar',   'ravi@gmail.com',   'pass3',  '9876543212', 'Chennai',     'Regular'),
 (4,  'Priya Sharma', 'priya@gmail.com',  'pass4',  '9876543213', 'Kolkata',     'Regular'),
 (5,  'Alok Yadav',   'alok@gmail.com',   'pass5',  '9876543214', 'Pune',        'Regular'),
 (6,  'Divya Singh',  'divya@gmail.com',  'pass6',  '9876543215', 'Jaipur',      'Regular'),
 (7,  'Karan Patel',  'karan@gmail.com',  'pass7',  '9876543216', 'Ahmedabad',   'Regular'),
 (8,  'Sneha Roy',    'sneha@gmail.com',  'pass8',  '9876543217', 'Bangalore',   'Regular'),
 (9,  'Manish Das',   'manish@gmail.com', 'pass9',  '9876543218', 'Hyderabad',   'Regular'),
 (10, 'Anjali Mehta',  'anjali@gmail.com', 'pass10', '9876543219', 'Lucknow',     'Regular'),
 (11, 'Rohit Jain',   'rohit@gmail.com',  'pass11', '9876543220', 'Surat',       'Regular'),
 (12, 'Simran Kaur',  'simran@gmail.com', 'pass12', '9876543221', 'Chandigarh',  'Regular'),
 (13, 'Vikram Rana',  'vikram@gmail.com', 'pass13', '9876543222', 'Nagpur',      'Regular'),
 (14, 'Megha Sethi',  'megha@gmail.com',  'pass14', '9876543223', 'Indore',      'Regular'),
 (15, 'Saurabh Joshi','saurabh@gmail.com','pass15', '9876543224', 'Bhopal',      'Regular');

-- ORDERS
INSERT INTO ORDERS (Order_ID, Customer_ID, Restaurant_ID, Payment_Method, Order_Date, Total_Amount, Order_Status) VALUES
 (1,  1,  1, 'Credit Card',       '2024-01-01', 782.65, 'Delivered'),
 (2, 12,  1, 'Cash on Delivery',  '2024-01-02', 504.29, 'Cancelled'),
 (3,  4,  3, 'Cash on Delivery',  '2024-01-03', 671.63, 'Cancelled'),
 (4,  7,  4, 'UPI',               '2024-01-04', 815.94, 'Out for Delivery'),
 (5, 15,  1, 'Credit Card',       '2024-01-05', 833.10, 'Pending'),
 (6,  1,  2, 'Credit Card',       '2024-01-06', 919.90, 'Delivered'),
 (7,  7,  4, 'UPI',               '2024-01-07', 746.11, 'Preparing'),
 (8,  5,  2, 'UPI',               '2024-01-08', 247.49, 'Delivered'),
 (9, 10,  1, 'Cash on Delivery',  '2024-01-09', 873.73, 'Out for Delivery'),
 (10,15,  1, 'Credit Card',       '2024-01-10', 826.12, 'Preparing'),
 (11,12,  1, 'Credit Card',       '2024-01-11', 968.68, 'Cancelled'),
 (12, 5,  2, 'Credit Card',       '2024-01-12', 372.01, 'Delivered'),
 (13, 9,  2, 'Credit Card',       '2024-01-13', 682.51, 'Pending'),
 (14,11,  1, 'Cash on Delivery',  '2024-01-14', 665.84, 'Preparing'),
 (15,12,  3, 'UPI',               '2024-01-15', 911.20, 'Pending'),
 (16, 6,  2, 'UPI',               '2024-01-16', 363.15, 'Delivered'),
 (17,13,  4, 'Cash on Delivery',  '2024-01-17', 937.95, 'Preparing'),
 (18,11,  1, 'Cash on Delivery',  '2024-01-18', 260.02, 'Delivered'),
 (19, 2,  2, 'Cash on Delivery',  '2024-01-19', 858.05, 'Out for Delivery'),
 (20,10,  3, 'Cash on Delivery',  '2024-01-20', 581.59, 'Pending');

-- ORDER_DETAIL
INSERT INTO ORDER_DETAIL (Order_Detail_ID, Order_ID, Food_ID, Quantity, Price) VALUES
 (1, 13,  3, 5, 210.63),
 (2,  3, 15, 4, 398.27),
 (3,  6,  9, 3, 105.20),
 (4, 17, 12, 4, 322.60),
 (5,  3, 19, 4, 160.49),
 (6, 19, 15, 2, 166.09),
 (7, 19, 14, 2, 126.73),
 (8, 13, 20, 1, 301.14),
 (9,  2, 20, 1, 329.30),
 (10,19, 19, 4, 123.76),
 (11, 8, 12, 2, 140.97),
 (12,10, 11, 3, 171.50),
 (13,17,  2, 4, 123.64),
 (14, 6,  9, 1, 246.08),
 (15, 3,  8, 1, 222.47),
 (16,11, 16, 2, 224.69),
 (17, 3, 15, 4, 222.78),
 (18,14,  1, 2, 126.02),
 (19,11, 14, 2, 330.21),
 (20, 4,  9, 4, 364.05);

-- PAYMENT_STATUS
INSERT INTO PAYMENT_STATUS (Payment_ID, Payment_Status, Payment_Method, Order_ID) VALUES
 (1,  'Failed',  'Cash on Delivery',  1),
 (2,  'Pending', 'Cash on Delivery',  2),
 (3,  'Paid',    'Cash on Delivery',  3),
 (4,  'Failed',  'Credit Card',        4),
 (5,  'Paid',    'Cash on Delivery',  5),
 (6,  'Paid',    'Cash on Delivery',  6),
 (7,  'Paid',    'Cash on Delivery',  7),
 (8,  'Paid',    'Cash on Delivery',  8),
 (9,  'Paid',    'Credit Card',        9),
 (10, 'Pending', 'Credit Card',       10),
 (11, 'Paid',    'Cash on Delivery', 11),
 (12, 'Paid',    'Cash on Delivery', 12),
 (13, 'Failed',  'UPI',              13),
 (14, 'Paid',    'Credit Card',      14),
 (15, 'Pending', 'Credit Card',      15),
 (16, 'Failed',  'Credit Card',      16),
 (17, 'Paid',    'UPI',              17),
 (18, 'Paid',    'Credit Card',      18),
 (19, 'Pending', 'Credit Card',      19),
 (20, 'Failed',  'Credit Card',      20);

-- REVIEW
INSERT INTO REVIEW (Review_ID, Customer_ID, Restaurant_ID, Review_Date, Rating, Comment1) VALUES
 (1,  2, 4, '2024-01-01', 3, 'Could be better.'),
 (2,  2, 1, '2024-01-02', 4, 'Excellent experience.'),
 (3,  2, 2, '2024-01-03', 4, 'Great service!'),
 (4, 13, 4, '2024-01-04', 1, 'Could be better.'),
 (5,  3, 2, '2024-01-05', 1, 'Great service!'),
 (6,  9, 4, '2024-01-06', 4, 'Not satisfied.'),
 (7,  6, 2, '2024-01-07', 5, 'Excellent experience.'),
 (8,  5, 2, '2024-01-08', 5, 'Average.'),
 (9,  5, 3, '2024-01-09', 5, 'Excellent experience.'),
 (10, 8, 2, '2024-01-10', 2, 'Good food!'),
 (11, 5, 3, '2024-01-11', 3, 'Average.'),
 (12, 6, 1, '2024-01-12', 4, 'Great service!');

-- DELIVERY_AGENT
INSERT INTO DELIVERY_AGENT (Agent_ID, Name, Phone_Number, Vehicle_Number, Availability_Status) VALUES
 (1, 'Agent_1', '900000001', 'VEH1XYZ', 'Y'),
 (2, 'Agent_2', '900000002', 'VEH2XYZ', 'N'),
 (3, 'Agent_3', '900000003', 'VEH3XYZ', 'N'),
 (4, 'Agent_4', '900000004', 'VEH4XYZ', 'Y'),
 (5, 'Agent_5', '900000005', 'VEH5XYZ', 'Y');

-- DELIVERY
INSERT INTO DELIVERY (Delivery_ID, Order_ID, Agent_ID, Pickup_Time, Delivery_Time, Delivery_Status) VALUES
 (1, 9,  3, DATETIME('now'),            DATETIME('now','+30 minutes'), 'Picked Up'),
 (2, 4,  3, DATETIME('now'),            DATETIME('now','+30 minutes'), 'Out for Delivery'),
 (3, 1,  1, DATETIME('now'),            DATETIME('now','+30 minutes'), 'Delivered'),
 (4, 12, 2, DATETIME('now'),            DATETIME('now','+30 minutes'), 'Out for Delivery'),
 (5, 5,  5, DATETIME('now'),            DATETIME('now','+30 minutes'), 'Delivered'),
 (6, 18, 3, DATETIME('now'),            DATETIME('now','+30 minutes'), 'Picked Up'),
 (7, 15, 2, DATETIME('now'),            DATETIME('now','+30 minutes'), 'Picked Up'),
 (8, 13, 1, DATETIME('now'),            DATETIME('now','+30 minutes'), 'Picked Up'),
 (9, 15, 1, DATETIME('now'),            DATETIME('now','+30 minutes'), 'Picked Up'),
 (10,18, 5, DATETIME('now'),            DATETIME('now','+30 minutes'), 'Out for Delivery'),
 (11,2,  3, DATETIME('now'),            DATETIME('now','+30 minutes'), 'Picked Up'),
 (12,6,  5, DATETIME('now'),            DATETIME('now','+30 minutes'), 'Picked Up'),
 (13,9,  3, DATETIME('now'),            DATETIME('now','+30 minutes'), 'Delivered'),
 (14,8,  3, DATETIME('now'),            DATETIME('now','+30 minutes'), 'Assigned'),
 (15,6,  5, DATETIME('now'),            DATETIME('now','+30 minutes'), 'Out for Delivery'),
 (16,19, 5, DATETIME('now'),            DATETIME('now','+30 minutes'), 'Picked Up'),
 (17,13, 1, DATETIME('now'),            DATETIME('now','+30 minutes'), 'Out for Delivery'),
 (18,13, 2, DATETIME('now'),            DATETIME('now','+30 minutes'), 'Assigned'),
 (19,17, 5, DATETIME('now'),            DATETIME('now','+30 minutes'), 'Picked Up'),
 (20,15, 5, DATETIME('now'),            DATETIME('now','+30 minutes'), 'Assigned');

COMMIT;
PRAGMA foreign_keys = ON;
