:80 {
	encode gzip

	handle_path /api/* {
		reverse_proxy api:8000
	}

	handle /admin* {
		basic_auth {
			admin __HASH__
		}
		root * /srv
		try_files {path} /index.html
		file_server
	}

	handle {
		root * /srv
		try_files {path} /index.html
		file_server
	}
}
