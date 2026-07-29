# Application data model

```mermaid
classDiagram
    class User {
        +string id
        +string name
        +string email
        +string passwordHash
        +string role
        +DateTime createdAt
    }

    class BankAccount {
        +string id
        +string userId
        +number balance
        +string currency
        +DateTime updatedAt
    }

    class Product {
        +string id
        +string name
        +string description
        +number price
        +string sku
        +int availableQuantity
        +string category
    }

    class Supplier {
        +string id
        +string name
        +string apiEndpoint
        +DateTime lastSyncAt
    }

    class OrderRequest {
        +string id
        +string userId
        +string text
        +string status
        +string assignedOrderId
        +DateTime createdAt
    }

    class Order {
        +string id
        +string userId
        +string accountId
        +number totalPrice
        +string status
        +DateTime createdAt
        +DateTime completedAt
    }

    class OrderItem {
        +string id
        +string orderId
        +string productId
        +int quantity
        +number unitPrice
        +number subtotal
    }

    User "1" --> "1" BankAccount
    User "1" --> "*" Order
    User "1" --> "*" OrderRequest
    Order "1" --> "*" OrderItem
    OrderItem "*" --> "1" Product
    Order "*" --> "1" BankAccount
    Supplier "1" --> "*" Product
```

## Plain English explanation

This app needs to remember who is using it, what they can buy, and what they have ordered.

- `User` represents a buyer who logs in and works with the app.
- `BankAccount` stores the buyer's assigned budget and current balance.
- `Product` is each catalogue item the simulated supplier offers.
- `Supplier` represents the external catalogue source or supplier API that provides the product list.
- `OrderRequest` captures the natural language order text the user or agent submits and tracks whether it was fulfilled.
- `Order` is the actual purchase transaction created to fulfill a request.
- `OrderItem` breaks an order into one or more product line items, including quantity and price.

Connections:

- A `User` has one `BankAccount` and can place many `Orders`.
- A `User` can also submit many `OrderRequest` texts for the app or agent to fulfill.
- An `Order` is paid from a `BankAccount` and contains many `OrderItem`s.
- Each `OrderItem` points to a `Product` from the catalogue.
- `Supplier` owns or supplies the available `Product`s, representing the external seller interface.

This model keeps the core domain simple while supporting catalogue browsing, budget-aware fulfillment, and natural language order capture.
