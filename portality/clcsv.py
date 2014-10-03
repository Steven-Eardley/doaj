# Class to wrap the Python CSV library
import csv

class ClCsv():

    # Store the csv contents in a list of tuples, [ (column_header, [contents]) ]
    data = []

    def __init__(self, file_path, mode='r+b'):
        self.data = []
        if type(file_path) == file:
            self.file_object = file_path
            if self.file_object.closed:
                self.file_object = open(self.file_object.name, mode)
            self.read_file()
        else:
            try:
                self.file_object = open(file_path, mode)
                self.read_file()
            except IOError:
                # If the file doesn't exist, force its creation
                self.file_object = open(file_path, 'w+b')

    def read_file(self):
        """
        Retrieve all of the information from the stored file using standard csv lib
        :return: Entire CSV contents, a list of rows (like the standard csv lib)
        """
        if self.file_object.closed:
            open(self.file_object.name, 'r+b')

        reader = csv.reader(self.file_object)
        rows = []
        for row in reader:
            rows.append(row)

        self._populate_data(rows)
        return rows


    def get_column(self, col_identifier):
        """
        Get a column from the CSV file.
        :param col_identifier: An int column index or a str column heading.
        :return: The column, as a { heading : [contents] } dict.
        """
        try:
            if type(col_identifier) == int:
                # get column by index
                return self.data[col_identifier]
            elif type(col_identifier) == str:
                # get column by title
                for col in self.data:
                    if col[0] == col_identifier:
                        return col
        except IndexError:
            return None


    def set_column(self, col_identifier, col_contents):
        """
        Set a column in the CSV file.
        :param col_identifier: An int column index or a str column heading.
        :param col_contents: The contents for the column
        """
        try:
            if type(col_identifier) == int:
                self.data[col_identifier] = (col_identifier, col_contents)
            elif type(col_identifier) == str:

                # set column by title. Raises IndexErrors like int indexes above.
                if len(self.data) == 0:
                    raise IndexError

                for i in range(0, len(self.data)):
                    (col_title, contents) = self.data[i]
                    if col_title == col_identifier:
                        self.data[i] = (col_identifier, col_contents)
                    else:
                        raise IndexError
        except IndexError:
            # The column isn't there already; append a new one
            if type(col_identifier) == int:
                self.data.append(col_contents)
            elif type(col_identifier) == str:
                self.data.append((col_identifier, col_contents))


    def get_colnumber(self, header):
        """
        Return the column number of a given header
        :param header:
        :return: The column number
        """
        for i in range(0, len(self.data)):
            if self.data[i][0] == header:
                return i


    def get_rownumber(self, first_col_val):
        """
        Get the row number of a given first column value, or none if not found
        :param first_col_val:
        :return: The row number
        """

        try:
            (col_name, col_contents) = self.data[0]
            col_data = [col_name] + col_contents
            return col_data.index(first_col_val)
        except ValueError:
            return None


    def save(self):
        """
        Write and close the file.
        """
        print "self.data:"
        print self.data
        rows = []
        for i in range(0, len(self.data)):
            row = []
            for (col_name, col_contents) in self.data:
                col_data = [col_name] + col_contents
                row.append(col_data[i])
            rows.insert(i, row)

        writer = csv.writer(self.file_object)
        writer.writerows(rows)
        self.file_object.close()


    def _populate_data(self, csv_rows):
        # Reset the stored data
        self.data = []
        for i in range(0, len(csv_rows[0])):
            col_data = []
            for row in csv_rows[1:]:
                col_data.append(row[i])
            self.data.append((csv_rows[0][i], col_data))

