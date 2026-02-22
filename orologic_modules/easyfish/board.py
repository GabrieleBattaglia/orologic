import chess
from .utils import CalculateMaterial

class CustomBoard(chess.Board):
    def __str__(self):
        board_str = "FEN: "+str(self.fen())+"\\n"
        white_material, black_material = CalculateMaterial(self)
        ranks = range(8, 0, -1) if self.turn == chess.WHITE else range(1, 9)
        files = range(8) if self.turn == chess.WHITE else range(7, -1, -1)
        
        for rank in ranks:
            board_str += str(rank)
            for file in files:
                square = chess.square(file, rank - 1)
                piece = self.piece_at(square)
                if piece:
                    symbol = piece.symbol()
                    if piece.color == chess.WHITE:
                        board_str += symbol.upper()
                    else:
                        board_str += symbol.lower()
                else:
                    board_str += "-" if (rank + file) % 2 == 0 else "+"
            board_str += "\\n"
        
        board_str += " abcdefgh" if self.turn == chess.WHITE else " hgfedcba"
        
        if self.fullmove_number == 1 and self.turn == chess.WHITE:
            last_move_info = "1.???"
        else:
            last_move_color = "White" if self.turn == chess.BLACK else "Black"
            move_number = self.fullmove_number - (1 if self.turn == chess.WHITE else 0)
            if self.move_stack:
                temp_board = chess.Board()
                for move in self.move_stack[:-1]:
                    temp_board.push(move)
                last_move_san = temp_board.san(self.move_stack[-1])
            else:
                last_move_san = "???"
            
            if self.turn == chess.BLACK:
                last_move_info = f"{move_number}. {last_move_san}"
            else:
                last_move_info = f"{move_number}... {last_move_san}"
                
        board_str += f" {last_move_info} Material: {white_material}/{black_material}"
        return board_str
