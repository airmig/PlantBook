# PlantBook 🌱

PlantBook is a modern web application designed to help plant enthusiasts track, share, and learn about their plants. The platform provides a user-friendly interface for managing your plant collection and connecting with other plant lovers.

## Live Demo

Visit [PlantBook](https://plantbook.onrender.com) to see the application in action.

## Features

- **User Authentication**: Secure login and registration system
- **Plant Directory**: Browse and search through a comprehensive collection of plants
- **Personal Plant Collection**: Track and manage your own plants
- **Community Sharing**: Share your plants with other users
- **Plant Details**: Access detailed information about each plant
- **Recently Added Plants**: Stay updated with the latest additions to the community

## Tech Stack

- **Backend**: Python (Django)
- **Database**: PostgreSQL
- **Deployment**: Render
- **Static Files**: Django Static Files
- **Media Storage**: Local/Cloud Storage

## Getting Started

### Prerequisites

- Python 3.8+
- PostgreSQL
- Docker (optional, for containerized deployment)

### Installation

1. Clone the repository:
```bash
git clone https://github.com/airmig/PlantBook.git
cd PlantBook
```

2. Set up a virtual environment and install dependencies:
```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

3. Configure environment variables:
Create a `.env` file in the root directory with the following variables:
```
DATABASE_URL=your_database_url
SECRET_KEY=your_secret_key
DEBUG=False
ALLOWED_HOSTS=your_domain
```

4. Set up the database:
```bash
python manage.py migrate
python manage.py collectstatic
```

5. Run the application:
```bash
python manage.py runserver
```

### Docker Deployment

To run the application using Docker:

```bash
docker-compose up --build
```

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Contact

Ariel Duran - [GitHub](https://github.com/yourusername)

---

© 2025 PlantBook. All rights reserved. 